from dataclasses import dataclass

from litewriter import LiteWriter
from stario import App, Context, Writer
from stario.datastar import SSE

from app.config import Config
from app.features.cam.urls import CAM
from app.features.home.urls import HOME, NEW_CAM, WATCH
from app.features.home.views import CODE_HINT, render
from app.features.watch.urls import WATCH_ROOM
from app.rooms import Rooms, parse_code, valid_code
from app.rooms.auth import cam_cookie_room, device_of, new_cam_key, set_cam_cookie
from app.rooms.data import add_room, cameras_of, hash_secret, prune_rooms


@dataclass(frozen=True, slots=True)
class HomePage:
    rooms: Rooms
    db: LiteWriter
    config: Config

    def register(self, app: App) -> None:
        app.add(HOME, self.show)
        app.add(NEW_CAM, self.new_cam)
        app.add(WATCH, self.watch)

    async def show(self, c: Context, w: Writer) -> None:
        device = device_of(self.db, c)
        cams = [
            (c[0], c[1] or "", self.rooms.cam_of(c[0]) is not None)
            for c in (cameras_of(self.db, device[0]) if device else [])
        ]
        w.html(render(self.config.og_image, "", cams))

    async def new_cam(self, c: Context, w: Writer) -> None:
        self.db.push(prune_rooms)
        code = cam_cookie_room(self.db, c)
        if code is None:
            key = new_cam_key()

            def make(tx) -> str | None:
                for _ in range(10):
                    candidate = self.rooms.random_code()
                    if tx.one("SELECT id FROM rooms WHERE id = :c", c=candidate) is None:
                        add_room(tx, candidate, hash_secret(key))
                        return candidate
                return None

            code = await self.db.write(make)
            if code is None:
                w.text("could not make a room, try again", status=503)
                return
            set_cam_cookie(c, w, code, key)
        SSE(w).navigate(CAM.href(code))

    async def watch(self, c: Context, w: Writer) -> None:
        code = parse_code(c.req.query.get("code", ""))
        if not valid_code(code):
            device = device_of(self.db, c)
            cams = [
                (c[0], c[1] or "", self.rooms.cam_of(c[0]) is not None)
                for c in (cameras_of(self.db, device[0]) if device else [])
            ]
            w.html(render(self.config.og_image, CODE_HINT, cams), status=400)
            return
        w.redirect(WATCH_ROOM.href(code), status=303)
