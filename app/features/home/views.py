from stario import h
from stario.datastar import at, data
from stario.markup import HtmlElement, classes

from app.common import icons
from app.common.shell import page
from app.common.ui import look_switch
from app.features.home.urls import NEW_CAM, WATCH

CODE_HINT = "That code has 6 digits. Try again."

_CHOICE = (
    "flex",
    "w-full",
    "items-center",
    "gap-4",
    "rounded-box",
    "border",
    "border-line",
    "bg-surface",
    "p-4",
    "text-left",
    "transition",
    "active:scale-[0.98]",
    "disabled:opacity-50",
    "motion-reduce:transition-none",
)


def _choice(icon, title: str, line: str, *attrs) -> HtmlElement:
    """One of the two answers: a large button with one line under its name."""
    return h.Button(
        {"type": "button"},
        classes(*_CHOICE),
        *attrs,
        icon(classes("size-8", "shrink-0", "text-accent")),
        h.Span(
            classes("flex", "min-w-0", "flex-col", "gap-0.5"),
            h.Span(classes("text-lg", "font-bold"), title),
            h.Span(classes("text-sm", "text-muted"), line),
        ),
    )


def _why() -> HtmlElement:
    return h.Section(
        classes("flex", "flex-col", "gap-4", "rounded-box", "bg-surface", "p-5"),
        h.H2(classes("text-lg", "font-bold"), "Why Philomena"),
        *[
            h.Div(
                classes("flex", "items-start", "gap-3"),
                icon(classes("mt-0.5", "size-5", "shrink-0", "text-accent")),
                h.Div(
                    classes("flex", "flex-col", "gap-0.5"),
                    h.P(classes("font-semibold"), bold),
                    h.P(classes("text-sm", "text-muted"), line),
                ),
            )
            for icon, bold, line in (
                (
                    icons.smartphone,
                    "No app to install.",
                    "Open this site on two phones. Add it to the home screen if you like.",
                ),
                (
                    icons.lock,
                    "Private by design.",
                    "Video and sound go straight between your phones, encrypted."
                    " Nothing is recorded.",
                ),
                (
                    icons.wifi,
                    "Works anywhere.",
                    "Home Wi-Fi or mobile data. When phones cannot reach each other"
                    " directly, an encrypted relay carries the sound and video.",
                ),
                (
                    icons.circle_check,
                    "Set up once.",
                    "The camera phone keeps its code, and phones you allowed reconnect"
                    " on their own.",
                ),
            )
        ],
    )


def render(og_image: str, error: str = "", cams: list | None = None) -> HtmlElement:
    return page(
        "Philomena — baby monitor",
        og_image,
        h.Main(
            {"id": "home"},
            classes(
                "mx-auto",
                "flex",
                "min-h-dvh",
                "w-full",
                "max-w-md",
                "flex-col",
                "gap-7",
                "p-4",
                "pt-[max(1rem,env(safe-area-inset-top))]",
                "pb-[max(1.5rem,env(safe-area-inset-bottom))]",
            ),
            data.signals({"_watch": bool(error), "_starting": False}, if_missing=True),
            h.Header(
                classes("flex", "items-center", "gap-2", "text-muted"),
                icons.moon(classes("size-5", "text-accent")),
                h.P(classes("font-semibold"), "Philomena"),
            ),
            h.Section(
                classes("flex", "flex-col", "gap-3"),
                h.H1(
                    classes(
                        "mb-1", "text-[1.75rem]", "leading-tight", "font-bold", "tracking-tight"
                    ),
                    "Which phone is this?",
                ),
                *(
                    [
                        h.Nav(
                            {"aria-label": "Your cameras"},
                            classes("list"),
                            h.P(classes("list-title"), "Your cameras"),
                            *[
                                h.A(
                                    {"href": f"/watch/{c[0]}"},
                                    h.Span(classes("status", "status-live" if c[2] else "")),
                                    h.Span(
                                        classes("min-w-0", "flex-1", "truncate"),
                                        c[1] or f"Camera {c[0][:3]} {c[0][3:]}",
                                    ),
                                    h.Span(
                                        classes("text-sm", "font-normal", "text-muted"),
                                        "Watch" if c[2] else "Off",
                                    ),
                                )
                                for c in cams
                            ],
                        )
                    ]
                    if cams
                    else []
                ),
                _choice(
                    icons.video,
                    "Stays with the baby",
                    "This phone becomes the camera.",
                    data.on("click", at.post(NEW_CAM.href())),
                    data.indicator("_starting"),
                    data.attr("disabled", "$_starting"),
                ),
                _choice(
                    icons.eye,
                    "Comes with me",
                    "Watch and listen from this phone.",
                    data.on("click", "$_watch = !$_watch"),
                    data.attr("aria-expanded", "$_watch"),
                ),
                h.Form(
                    {"method": "get", "action": WATCH.href()},
                    classes("flex", "flex-col", "gap-3", "rounded-box", "bg-surface", "p-4"),
                    data.show("$_watch"),
                    data.effect("$_watch && el.querySelector('input')?.focus()"),
                    h.Label(
                        {"for": "code"},
                        classes("text-sm", "text-muted"),
                        "The 6-digit code on the camera phone, or its link",
                    ),
                    h.Input(
                        {
                            "id": "code",
                            "type": "text",
                            "name": "code",
                            "inputmode": "numeric",
                            "required": True,
                            "autocomplete": "off",
                            "placeholder": "482 913",
                            "aria-label": "6-digit code or link",
                        },
                        # a pasted link or "482 913" becomes the 6 digits
                        data.on("input", "el.value = app.share.code(el.value)"),
                        classes(
                            "input",
                            "input-lg",
                            "w-full",
                            "text-center",
                            "font-mono",
                            "text-2xl",
                            "tracking-widest",
                        ),
                    ),
                    *(
                        [
                            h.P(
                                {"role": "alert"},
                                classes("text-center", "font-semibold", "text-alarm"),
                                error,
                            )
                        ]
                        if error
                        else []
                    ),
                    h.Button(
                        {"type": "submit"},
                        classes("btn", "btn-primary", "btn-lg", "btn-block"),
                        icons.eye(classes("size-5")),
                        "Watch",
                    ),
                ),
            ),
            h.Ol(
                classes("list-decimal", "space-y-2", "pl-5", "text-sm", "text-muted"),
                h.Li("Put the camera phone near the crib, plugged in."),
                h.Li("On your phone, choose Comes with me."),
                h.Li("Type the code the camera shows."),
            ),
            h.Div(
                {"role": "status"},
                classes("alert"),
                data.show("($_installable || $_ios_hint) && !$_install_gone"),
                h.Span(
                    classes("flex", "items-center", "gap-2"),
                    icons.share(classes("size-5", "shrink-0", "text-accent")),
                    h.Span(
                        data.show("$_ios_hint && !$_installable"),
                        "Add to Home Screen: tap Share, then Add to Home Screen.",
                    ),
                    h.Span(data.show("$_installable"), "Install for alerts on a locked phone."),
                ),
                h.Button(
                    {"type": "button"},
                    classes("btn", "btn-primary", "btn-sm"),
                    data.show("$_installable"),
                    data.on("click", "app.install.prompt(v => $_installable = v)"),
                    "Install",
                ),
                h.Button(
                    {"type": "button"},
                    classes("btn", "btn-ghost", "btn-sm"),
                    data.on("click", "$_install_gone = true; app.install.dismiss()"),
                    "Dismiss",
                ),
            ),
            # a parent who already has a camera knows why
            *([] if cams else [_why()]),
            h.Section(
                classes("flex", "flex-col", "gap-2"),
                h.H2(classes("text-sm", "font-semibold"), "Look"),
                look_switch(),
                h.P(
                    classes("text-xs", "text-muted"),
                    "Night is black and red, the least light that works in a dark room."
                    " Day is black on white, for bright light. Auto follows this phone.",
                ),
            ),
            h.P(classes("text-sm", "text-muted"), "Built by Adam, a dad of three."),
        ),
    )
