import re
import uuid
from dataclasses import dataclass

from litewriter import LiteWriter, Tx
from stario import App, Context, Relay, Writer
from stario.datastar import SSE, read_signals

from app.config import Config
from app.features.cam.urls import (
    CAM,
    CAM_APPROVE,
    CAM_LIVE,
    CAM_NAME,
    CAM_NEW_CODE,
    CAM_REMOVE,
)
from app.features.cam.views import (
    render,
    render_forbidden,
    render_knocks,
    render_viewers,
)
from app.push.data import delete_of as delete_subs
from app.push.data import delete_room as delete_subs_room
from app.push.handlers import Push
from app.rooms import Rooms, receive_script, valid_code
from app.rooms.auth import cam_owner, new_cam_key, set_cam_cookie
from app.rooms.data import (
    add_room,
    approval_devices,
    approval_status,
    approvals_for,
    approve,
    delete_room,
    hash_secret,
    remove_approval,
    room_name,
    room_row,
    set_room_name,
    touch_room,
)
from app.rooms.ice import ice_servers

_HOST_RE = re.compile(r"[A-Za-z0-9.\-]+(:\d{1,5})?")


def _valid_device_id(device_id: str) -> bool:
    return device_id.isalnum() and len(device_id) <= 32


def watch_url(c: Context, code: str) -> str | None:
    """The absolute watch link for the QR code, from a trusted Host header."""
    host = c.req.headers.get("host", "")
    if not _HOST_RE.fullmatch(host):
        return None
    local = host.split(":", 1)[0] in ("localhost", "127.0.0.1")
    proto = "https" if c.req.headers.get("x-forwarded-proto") == "https" or not local else "http"
    return f"{proto}://{host}/watch/{code}"


@dataclass(frozen=True, slots=True)
class CamPage:
    rooms: Rooms
    relay: Relay[dict]
    config: Config
    db: LiteWriter
    push: Push

    def register(self, app: App) -> None:
        app.add(CAM, self.show)
        app.add(CAM_LIVE, self.live)
        app.add(CAM_NEW_CODE, self.new_code)
        app.add(CAM_APPROVE, self.approve)
        app.add(CAM_REMOVE, self.remove)
        app.add(CAM_NAME, self.cam_name)

    async def show(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        if not valid_code(code):
            w.text("code must be 6 digits", status=400)
            return
        if room_row(self.db, code) is None:
            w.text("no such room", status=404)
            return
        if not cam_owner(self.db, c, code):
            w.html(render_forbidden(self.config.og_image), status=403)
            return
        w.html(
            render(
                code,
                uuid.uuid7().hex,
                approvals_for(self.db, code),
                self.rooms.devices_online(code),
                watch_url(c, code),
                self.config.og_image,
                room_name(self.db, code),
            )
        )

    async def live(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        tab = str((await read_signals(c.req)).get("tab", ""))
        if not valid_code(code) or not (tab.isalnum() and len(tab) <= 32):
            w.text("bad room or tab", status=400)
            return
        if not cam_owner(self.db, c, code):
            w.text("this camera belongs to another phone", status=403)
            return
        async with self.relay.subscribe(f"peer.{tab}", f"panel.{code}") as events:
            sse = SSE(w)
            sse.execute_script(receive_script({"type": "ice", "data": ice_servers(self.config)}))
            self.db.push(touch_room, code)
            self.repaint(sse, code)
            old = self.rooms.cam_join(code, tab)
            self.push.cam_back(code)
            if old is not None:
                self.relay.publish(f"peer.{old}", {"type": "replaced"})
            for viewer in self.rooms.viewers_of(code):
                self.relay.publish(f"peer.{viewer}", {"type": "cam", "data": True})
                self.relay.publish(f"peer.{tab}", {"type": "join", "from": viewer})
            try:
                async for subject, msg in c.alive(events):
                    if subject == f"panel.{code}":
                        self.repaint(sse, code)
                        continue
                    sse.execute_script(receive_script(msg))
                    if msg.get("type") in ("join", "leave"):
                        self.repaint(sse, code)
            finally:
                self.rooms.leave(code, tab)
                self.push.cam_gone(code, c.app)
                # A stale stream of a replaced cam must not report cam:false.
                if self.rooms.cam_of(code) is None:
                    for viewer in self.rooms.viewers_of(code):
                        self.relay.publish(f"peer.{viewer}", {"type": "cam", "data": False})

    def repaint(self, sse: SSE, code: str) -> None:
        approvals = approvals_for(self.db, code)
        online = self.rooms.devices_online(code)
        sse.patch_elements(render_knocks(approvals, code))
        sse.patch_elements(render_viewers(approvals, online, code))
        sse.patch_signals({"_pending": sum(a.status == "pending" for a in approvals)})

    async def cam_name(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        if not cam_owner(self.db, c, code):
            w.text("this camera belongs to another phone", status=403)
            return
        name = str((await read_signals(c.req)).get("name", "")).strip()
        if len(name) > 30:
            w.text("name is too long", status=400)
            return
        await self.db.write(set_room_name, code, name)
        self.relay.publish(f"panel.{code}", {"type": "name"})
        for viewer in self.rooms.viewers_of(code):
            self.relay.publish(f"peer.{viewer}", {"type": "name", "data": name})
        w.empty()

    async def new_code(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        if not valid_code(code):
            w.text("code must be 6 digits", status=400)
            return
        if not cam_owner(self.db, c, code):
            w.text("this camera belongs to another phone", status=403)
            return
        old_device_ids = approval_devices(self.db, code)
        key = new_cam_key()

        def replace(tx: Tx) -> str | None:
            delete_room(tx, code)
            delete_subs_room(tx, code)
            for _ in range(10):
                new = self.rooms.random_code()
                if tx.one("SELECT id FROM rooms WHERE id = :c", c=new) is None:
                    add_room(tx, new, hash_secret(key))
                    return new
            return None

        new = await self.db.write(replace)
        if new is None:
            w.text("could not make a room, try again", status=503)
            return
        for device_id in old_device_ids:
            self.relay.publish(f"device.{code}.{device_id}", {"type": "removed"})
        set_cam_cookie(c, w, new, key)
        SSE(w).navigate(CAM.href(new))

    async def approve(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        device_id = c.match.params["device_id"]
        if not valid_code(code) or not _valid_device_id(device_id):
            w.text("bad ids", status=400)
            return
        if not cam_owner(self.db, c, code):
            w.text("this camera belongs to another phone", status=403)
            return
        if approval_status(self.db, code, device_id) is None:
            w.text("no such device", status=404)
            return
        w.empty()
        await self.db.write(approve, code, device_id)
        self.relay.publish(f"device.{code}.{device_id}", {"type": "approved"})
        self.relay.publish(f"panel.{code}", {})

    async def remove(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        device_id = c.match.params["device_id"]
        if not valid_code(code) or not _valid_device_id(device_id):
            w.text("bad ids", status=400)
            return
        if not cam_owner(self.db, c, code):
            w.text("this camera belongs to another phone", status=403)
            return
        if approval_status(self.db, code, device_id) is None:
            w.text("no such device", status=404)
            return
        w.empty()
        await self.db.write(remove_approval, code, device_id)
        await self.db.write(delete_subs, code, device_id)
        cam = self.rooms.cam_of(code)
        if cam is not None:
            for tab in self.rooms.device_tabs(code, device_id):
                self.relay.publish(f"peer.{cam}", {"type": "kick", "from": tab})
        self.relay.publish(f"device.{code}.{device_id}", {"type": "removed"})
        self.relay.publish(f"panel.{code}", {})
