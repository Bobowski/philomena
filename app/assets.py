from pathlib import Path

from stario import Assets

ASSETS = Assets(Path(__file__).resolve().parents[1] / "static", url_prefix="/static")
STYLE_CSS = ASSETS.href("css/output.css")
DATASTAR_JS = ASSETS.href("js/datastar.js")
# runs in <head> before the first paint: it sets the night or day look
THEME_JS = ASSETS.href("js/theme.js")
ICON_192 = ASSETS.href("icons/icon-192.png")
ICON_512 = ASSETS.href("icons/icon-512.png")
ICON_MASKABLE_512 = ASSETS.href("icons/icon-maskable-512.png")
APPLE_TOUCH_ICON = ASSETS.href("icons/apple-touch-icon.png")
OG_IMAGE = ASSETS.href("og.png")
# Client behaviour lives in static/js/<name>.js — each file defines app.<name>.
SCRIPTS = tuple(
    ASSETS.href(f"js/{name}.js")
    for name in (
        "rtc",
        "wake",
        "share",
        "pwa",
        "night",
        "idle",
        "sound",
        "view",
        "install",
        "motion",
        "detect",
        "timeline",
        "nightChart",
        "push",
        "glance",
    )
)
