from dataclasses import dataclass

from stario import App, Context, Writer
from stario.json import dumps_bytes

from app.assets import ICON_192, ICON_512, ICON_MASKABLE_512
from app.common.shell import THEME_COLOR
from app.features.pwa.urls import HEALTH, MANIFEST, SW_JS


def manifest_json() -> bytes:
    return dumps_bytes(
        {
            "name": "Philomena",
            "short_name": "Philomena",
            "start_url": "/",
            "display": "standalone",
            "background_color": THEME_COLOR,
            "theme_color": THEME_COLOR,
            "icons": [
                {"src": ICON_192, "sizes": "192x192", "type": "image/png"},
                {"src": ICON_512, "sizes": "512x512", "type": "image/png"},
                {
                    "src": ICON_MASKABLE_512,
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class PwaPage:
    manifest: bytes
    sw_js: bytes

    def register(self, app: App) -> None:
        app.add(MANIFEST, self.manifest_route)
        app.add(SW_JS, self.sw)
        app.add(HEALTH, self.health)

    async def manifest_route(self, c: Context, w: Writer) -> None:
        w.respond(self.manifest, b"application/manifest+json")

    async def sw(self, c: Context, w: Writer) -> None:
        w.respond(self.sw_js, b"text/javascript")

    async def health(self, c: Context, w: Writer) -> None:
        w.text("ok")
