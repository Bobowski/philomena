"""The parts every page shares: the top bar, a sheet, a tile, and the look switch."""

from stario import h
from stario.datastar import data
from stario.markup import HtmlElement, classes

from app.common import icons

_LOOKS = (
    ("auto", icons.contrast, "Auto"),
    ("night", icons.moon, "Night"),
    ("day", icons.sun, "Day"),
)


def top_bar(
    back: str, title: str, status: str, dot: dict[str, str], *attrs, end: tuple = ()
) -> HtmlElement:
    """One row: Back, the room name, the status, and `end` on the right.

    `title` and `status` are expressions. The name gives way first: the status stays whole.
    """
    return h.Header(
        {"data-part": "bar"},
        classes(
            "absolute",
            "inset-x-0",
            "top-0",
            "z-30",
            "flex",
            "items-center",
            "gap-1",
            "border-b",
            "border-line",
            "bg-surface/90",
            "px-2",
            "pt-[max(0.5rem,env(safe-area-inset-top))]",
            "pb-2",
            "backdrop-blur",
        ),
        *attrs,
        h.Button(
            {"type": "button", "aria-label": "Back to start"},
            classes("btn", "btn-ghost", "btn-circle"),
            data.on("click", back),
            icons.chevron_left(classes("size-6")),
        ),
        h.Div(
            classes("flex", "min-w-0", "flex-1", "items-center", "gap-3"),
            h.P(classes("min-w-0", "truncate", "font-semibold"), data.text(title)),
            h.P(
                {"role": "status"},
                classes(
                    "flex", "shrink-0", "items-center", "gap-1.5", "text-sm", "whitespace-nowrap"
                ),
                h.Span(
                    classes("status", "shrink-0", "motion-reduce:animate-none"),
                    data.classes(dot),
                ),
                h.Span(classes("text-muted"), data.text(status)),
            ),
        ),
        *end,
    )


def sheet(ref: str, heading: str | HtmlElement, *body, on: tuple = ()) -> HtmlElement:
    """A bottom sheet with a heading, a close control, and a body that fits without scroll."""
    return h.Dialog(
        classes("sheet"),
        data.ref(ref),
        *on,
        h.Form(
            {"method": "dialog"},
            classes("sheet-backdrop"),
            h.Button({"aria-label": "Close", "tabindex": "-1"}, "close"),
        ),
        h.Div(
            classes("sheet-box"),
            h.Div(
                classes("flex", "items-center", "justify-between", "gap-2"),
                h.H3(classes("text-lg", "font-bold"), heading),
                h.Button(
                    {"type": "button", "aria-label": "Close"},
                    classes("btn", "btn-circle", "btn-ghost"),
                    data.on("click", f"${ref}.close()"),
                    icons.x(classes("size-5")),
                ),
            ),
            *body,
        ),
    )


def tile(label: str | HtmlElement, click: str, *marks, on: str = "", show: str = "") -> HtmlElement:
    """A square control. A toggle passes `on`: it fills while on."""
    return h.Button(
        {"type": "button", "data-tile": True},
        classes("tile"),
        *([data.show(show)] if show else []),
        *([data.attr("aria-pressed", f"({on}) ? 'true' : 'false'")] if on else []),
        data.on("click", click),
        *marks,
        h.Span(label) if isinstance(label, str) else label,
    )


def look_switch(*attrs) -> HtmlElement:
    """Auto, Night, or Day. Auto follows the phone's light or dark setting."""
    return h.Div(
        {"role": "group", "aria-label": "Look"},
        classes("seg"),
        *attrs,
        *[
            h.Button(
                {"type": "button"},
                data.attr("aria-pressed", f"$_theme === '{key}' ? 'true' : 'false'"),
                data.on("click", f"app.theme.set('{key}')"),
                icon(classes("size-4")),
                label,
            )
            for key, icon, label in _LOOKS
        ],
    )
