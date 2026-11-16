"""Push routes: subscribe, kinds, off, cam events, camera-offline."""

import asyncio
import json
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

from litewriter import LiteWriter
from stario import App, Context, Writer
from stario.datastar import read_signals

from app.config import Config
from app.push.data import add_sub, delete_endpoint, delete_of, set_kinds, subs_for
from app.push.sender import PushSender
from app.push.urls import CAM_EVENTS, PUSH_KINDS, PUSH_OFF, PUSH_SUB
from app.rooms import Rooms
from app.rooms.auth import cam_cookie_room, device_of
from app.rooms.data import approval_status, room_name

# only real push services may receive our posts (SSRF guard)
ALLOWED_HOSTS = (
    "fcm.googleapis.com",
    "android.googleapis.com",
    "push.apple.com",
    "push.services.mozilla.com",
    "notify.windows.com",
)
SUB_KINDS = {"crying", "stirring", "loud", "movement", "lights", "offline"}
EVENT_KINDS = {
    "crying": "crying",
    "stirring": "stirring",
    "loud": "loud",
    "movement": "movement",
    "lights_on": "lights",
    "lights_off": "lights",
}
COOLDOWNS = {
    "crying": 120,
    "stirring": 300,
    "loud": 60,
    "movement": 60,
    "lights": 60,
    "offline": 60,
}
PER_MINUTE = 6


def _host_ok(endpoint: str) -> bool:
    try:
        url = urlparse(endpoint)
    except ValueError:
        return False
    try:
        port = url.port
    except ValueError:
        return False
    return (
        url.scheme == "https"
        and port in (None, 443)
        and any(
            (url.hostname or "") == h or (url.hostname or "").endswith("." + h)
            for h in ALLOWED_HOSTS
        )
    )


@dataclass(frozen=True, slots=True)
class Push:
    rooms: Rooms
    db: LiteWriter
    sender: PushSender
    config: Config
    _last: dict = field(default_factory=dict)
    _minute: dict = field(default_factory=dict)

    def register(self, app: App) -> None:
        app.add(PUSH_SUB, self.subscribe)
        app.add(PUSH_KINDS, self.kinds)
        app.add(PUSH_OFF, self.off)
        app.add(CAM_EVENTS, self.cam_event)

    def _device(self, c: Context, code: str) -> str | None:
        """The approved device's id, or None."""
        device_id = c.req.cookies.get("device", "").partition(".")[0]
        if not device_id or not device_of(self.db, c):
            return None
        if approval_status(self.db, code, device_id) != "approved":
            return None
        return device_id

    async def subscribe(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        device = self._device(c, code)
        if not device:
            return w.text("approve this phone first", status=403)
        body = await read_signals(c.req)
        sub = body.get("subscription") or {}
        kinds = body.get("kinds") or []
        keys = sub.get("keys") or {}
        endpoint = sub.get("endpoint") or ""
        if (
            not isinstance(endpoint, str)
            or not endpoint
            or len(endpoint) > 1024
            or not _host_ok(endpoint)
            or not isinstance(keys.get("p256dh"), str)
            or not isinstance(keys.get("auth"), str)
            or not set(kinds) <= SUB_KINDS
        ):
            return w.text("bad subscription", status=400)
        await self.db.write(add_sub, code, device, {"endpoint": endpoint, "keys": keys}, kinds)
        w.empty()

    async def kinds(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        device = self._device(c, code)
        if not device:
            return w.text("approve this phone first", status=403)
        kinds = (await read_signals(c.req)).get("kinds") or []
        if not set(kinds) <= SUB_KINDS:
            return w.text("bad kinds", status=400)
        await self.db.write(set_kinds, code, device, kinds)
        w.empty()

    async def off(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        device = self._device(c, code)
        if not device:
            return w.text("approve this phone first", status=403)
        await self.db.write(delete_of, code, device)
        w.empty()

    async def cam_event(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        if cam_cookie_room(self.db, c) != code:
            return w.text("not the camera", status=403)
        body = await read_signals(c.req)
        kind = EVENT_KINDS.get(str(body.get("kind") or ""))
        at = body.get("at")
        if not kind or not isinstance(at, (int, float)):
            return w.text("bad event", status=400)
        w.empty()
        now = time.monotonic()
        key = (code, kind)
        if now - self._last.get(key, -1e9) < COOLDOWNS[kind]:
            return
        sent = [t for t in self._minute.get(code, []) if now - t < 60]
        if len(sent) >= PER_MINUTE:
            return
        self._last[key] = now
        sent.append(now)
        self._minute[code] = sent
        c.app.create_task(self.send_all(code, kind, at))

    async def send_all(self, code: str, kind: str, at: float, body: str = "") -> None:
        payload = {
            "title": room_name(self.db, code) or "Philomena",
            "kind": kind,
            "at": at,
            "url": f"/watch/{code}",
        }
        if body:
            payload["body"] = body
        for _did, endpoint, p256dh, auth, kinds_raw in subs_for(self.db, code):
            kinds = json.loads(kinds_raw or "[]")
            if kind not in kinds:
                continue
            sub = {"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}
            status = await asyncio.to_thread(self.sender.send, sub, payload)
            if status in (404, 410):
                await self.db.write(delete_endpoint, code, endpoint)

    def cam_back(self, code: str) -> None:
        task = self.rooms.offline_tasks.pop(code, None)
        if task:
            task.cancel()

    def cam_gone(self, code: str, app: App) -> None:
        # One timer per room: a second drop restarts it instead of sending twice.
        self.cam_back(code)
        self.rooms.offline_tasks[code] = app.create_task(self._offline_later(code, app))

    async def _offline_later(self, code: str, app: App) -> None:
        """Push "offline" when the camera stays away. A shutdown is not an offline camera."""
        try:
            # `shutdown` is a shield: the timeout cancels it, not the app's future.
            await asyncio.wait_for(app.shutdown, self.config.offline_push_after)
        except TimeoutError:
            pass
        else:
            return
        self.rooms.offline_tasks.pop(code, None)
        if self.rooms.cam_of(code) is None:
            await self.send_all(code, "offline", time.time() * 1000, "The camera is offline.")
