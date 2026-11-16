import asyncio

from litewriter import LiteWriter, Tx
from stario import App, Relay, Span, serve
from stario.http import same_origin, security_headers

from app.assets import ASSETS
from app.config import Config
from app.features.cam.handlers import CamPage
from app.features.home.handlers import HomePage
from app.features.pwa.handlers import PwaPage, manifest_json
from app.features.room.handlers import RoomPage
from app.features.watch.handlers import WatchPage
from app.push.data import schema as push_schema
from app.push.handlers import Push
from app.push.sender import PushSender
from app.push.vapid import load as load_vapid
from app.rooms import Rooms
from app.rooms import data as rooms_data


def schema(tx: Tx) -> None:
    rooms_data.schema(tx)
    push_schema(tx)


async def bootstrap(app: App, span: Span):
    config = Config.from_env()
    app.use("/", same_origin(), security_headers())
    async with LiteWriter(config.db_path, schema=schema, claim=30) as db:
        span.attrs(await ASSETS.attach(app))
        rooms = Rooms()
        pem_path, vapid_pub = load_vapid(config.data_dir / "vapid.pem")
        push = Push(rooms, db, PushSender(pem_path, config.public_url), config)
        push.register(app)
        relay: Relay[dict] = Relay()
        HomePage(rooms, db, config).register(app)
        CamPage(rooms, relay, config, db, push).register(app)
        WatchPage(rooms, relay, config, db, vapid_pub).register(app)
        RoomPage(rooms, relay).register(app)
        PwaPage(manifest_json(), (ASSETS.directory / "sw.js").read_bytes()).register(app)
        yield


if __name__ == "__main__":
    asyncio.run(serve(bootstrap))
