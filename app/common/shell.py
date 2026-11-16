from stario import h
from stario.datastar import ModuleScript, data
from stario.markup import HtmlElement, baked, classes

from app.assets import APPLE_TOUCH_ICON, DATASTAR_JS, SCRIPTS, STYLE_CSS, THEME_JS
from app.features.pwa.urls import MANIFEST

# The night ground. The browser chrome follows the look: theme.js swaps it for day.
THEME_COLOR = "#000000"
DESCRIPTION = "A baby monitor from two phones. Private, encrypted, nothing to install."


@baked
def page(title: str, og_image: str, body: HtmlElement) -> HtmlElement:
    return h.HtmlDocument(
        {"lang": "en", "data-theme": "night"},
        h.Head(
            h.Meta({"charset": "utf-8"}),
            h.Meta(
                {
                    "name": "viewport",
                    "content": "width=device-width, initial-scale=1, viewport-fit=cover",
                }
            ),
            h.Meta({"name": "theme-color", "content": THEME_COLOR}),
            # before the stylesheet and without defer: the first paint has the right look
            h.Script({"src": THEME_JS}),
            h.Meta({"name": "mobile-web-app-capable", "content": "yes"}),
            h.Meta({"name": "apple-mobile-web-app-capable", "content": "yes"}),
            h.Meta(
                {
                    "name": "apple-mobile-web-app-status-bar-style",
                    "content": "black-translucent",
                }
            ),
            h.Meta({"name": "apple-mobile-web-app-title", "content": "Philomena"}),
            h.Meta({"name": "description", "content": DESCRIPTION}),
            h.Meta({"property": "og:site_name", "content": "Philomena"}),
            h.Meta({"property": "og:title", "content": title}),
            h.Meta({"property": "og:description", "content": DESCRIPTION}),
            h.Meta({"property": "og:type", "content": "website"}),
            h.Meta({"property": "og:image", "content": og_image}),
            h.Meta({"property": "og:image:width", "content": "1200"}),
            h.Meta({"property": "og:image:height", "content": "630"}),
            h.Meta({"name": "twitter:card", "content": "summary_large_image"}),
            h.Link({"rel": "manifest", "href": MANIFEST.href()}),
            h.Link({"rel": "apple-touch-icon", "href": APPLE_TOUCH_ICON}),
            h.Title(title),
            h.Link({"rel": "stylesheet", "href": STYLE_CSS}),
            *[h.Script({"src": src, "defer": True}) for src in SCRIPTS],
            ModuleScript(DATASTAR_JS),
        ),
        h.Body(
            classes("min-h-dvh", "bg-ground", "text-ink"),
            data.init(
                "app.pwa.register(); app.install.wire(v => $_installable = v, v => $_ios_hint = v);"
                " app.theme.watch(m => $_theme = m)"
            ),
            data.signals(
                {
                    "_installable": False,
                    "_ios_hint": False,
                    "_install_gone": False,
                    "_theme": "auto",
                },
                if_missing=True,
            ),
            data.on(
                "beforeinstallprompt",
                "app.install.capture(evt, v => $_installable = v)",
                target="window",
            ),
            body,
            h.Div(
                classes("toast"),
                data.show("$_toast"),
                h.Output(
                    classes("alert", "shadow-lg"),
                    {"role": "status"},
                    data.signals({"_toast": ""}, if_missing=True),
                    data.text("$_toast"),
                    data.effect("$_toast && setTimeout(() => $_toast = '', 4000)"),
                ),
            ),
        ),
    )
