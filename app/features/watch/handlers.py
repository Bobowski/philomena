import uuid
from dataclasses import dataclass

from litewriter import LiteWriter
from stario import App, Context, Relay, Writer
from stario.datastar import SSE, read_signals

from app.config import Config
from app.features.watch.urls import WATCH_LIVE, WATCH_NAME, WATCH_ROOM
from app.features.watch.views import render, render_no_room
from app.rooms import Rooms, receive_script, valid_code
from app.rooms.auth import (
    device_name_from_ua,
    device_of,
    set_device_cookie,
)
from app.rooms.data import (
    approval_status,
    cameras_of,
    new_device,
    room_name,
    room_row,
    set_device_name,
    upsert_pending,
)
from app.rooms.ice import ice_servers


@dataclass(frozen=True, slots=True)
class WatchPage:
    rooms: Rooms
    relay: Relay[dict]
    config: Config
    db: LiteWriter
    vapid: str

    def register(self, app: App) -> None:
        app.add(WATCH_ROOM, self.show)
        app.add(WATCH_LIVE, self.live)
        app.add(WATCH_NAME, self.name)

    async def show(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        if not valid_code(code):
            w.text("code must be 6 digits", status=400)
            return
        if room_row(self.db, code) is None:
            w.html(render_no_room(code, self.config.og_image), status=404)
            return
        device = device_of(self.db, c)
        if device is None:
            name = device_name_from_ua(c.req.headers.get("user-agent", ""))
            device_id, token = await self.db.write(new_device, name)
            set_device_cookie(c, w, device_id, token)
            device = (device_id, "", name)
        cams = [
            (c[0], c[1] or "", self.rooms.cam_of(c[0]) is not None)
            for c in cameras_of(self.db, device[0])
        ]
        w.html(
            render(
                code,
                uuid.uuid7().hex,
                device[2] or "This phone",
                self.config.og_image,
                self.vapid,
                room_name(self.db, code),
                cams,
            )
        )

    async def live(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        tab = str((await read_signals(c.req)).get("tab", ""))
        if not valid_code(code) or not (tab.isalnum() and len(tab) <= 32):
            w.text("bad room or tab", status=400)
            return
        if room_row(self.db, code) is None:
            w.text("no such room", status=404)
            return
        device = device_of(self.db, c)
        if device is None:
            w.text("unknown device", status=403)
            return
        device_id = device[0]
        approved = approval_status(self.db, code, device_id) == "approved"
        async with self.relay.subscribe(f"peer.{tab}", f"device.{code}.{device_id}") as events:
            sse = SSE(w)
            sse.execute_script(receive_script({"type": "ice", "data": ice_servers(self.config)}))
            registered = False

            def join_viewer() -> None:
                nonlocal registered
                self.rooms.viewer_join(code, tab, device_id)
                cam = self.rooms.cam_of(code)
                sse.execute_script(receive_script({"type": "cam", "data": cam is not None}))
                if cam is not None:
                    self.relay.publish(f"peer.{cam}", {"type": "join", "from": tab})
                registered = True

            if approved:
                join_viewer()
            else:
                knocked = await self.db.write(upsert_pending, code, device_id)
                sse.execute_script(receive_script({"type": "pending"}))
                cam = self.rooms.cam_of(code)
                self.relay.publish(f"panel.{code}", {})
                if knocked and cam is not None:
                    self.relay.publish(f"peer.{cam}", {"type": "knock"})
            try:
                async for subject, msg in c.alive(events):
                    if subject == f"device.{code}.{device_id}":
                        kind = msg.get("type")
                        if kind == "approved" and not registered:
                            join_viewer()
                        elif kind == "removed":
                            sse.execute_script(receive_script({"type": "removed"}))
                            return
                        continue
                    if not registered:
                        continue  # a pending tab gets no signals
                    sse.execute_script(receive_script(msg))
            finally:
                if registered:
                    self.rooms.leave(code, tab)
                    cam = self.rooms.cam_of(code)
                    if cam is not None:
                        self.relay.publish(f"peer.{cam}", {"type": "leave", "from": tab})

    async def name(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        if not valid_code(code):
            w.text("code must be 6 digits", status=400)
            return
        device = device_of(self.db, c)
        if device is None:
            w.text("unknown device", status=403)
            return
        signals = await read_signals(c.req)
        name = str(signals.get("name", "")).strip()[:30]
        w.empty()
        if name:
            await self.db.write(set_device_name, device[0], name)
            self.relay.publish(f"panel.{code}", {})
