from stario import h
from stario.datastar import at, data
from stario.markup import HtmlElement, classes

from app.common import icons
from app.common.shell import page
from app.common.ui import look_switch, sheet, tile, top_bar
from app.features.home.urls import HOME
from app.features.watch.urls import WATCH_LIVE, WATCH_NAME

_WAITING_TEXT = (
    "$_state === 'lost' ? 'Reconnecting…'"
    " : $_state === 'connecting' ? 'Connecting…'"
    " : ($_cam_name ? 'Waiting for ' + $_cam_name : 'Waiting for the camera')"
)

_LIVE_TEXT = (
    "$_state === 'live' ? 'Live' + ($_live_for ? ' · ' + $_live_for : '')"
    " : $_state === 'lost' ? 'Reconnecting…'"
    " : $_state === 'connecting' ? 'Connecting…'"
    " : ($_cam_name ? 'Waiting for ' + $_cam_name : 'Waiting for the camera')"
)

# the status beside the camera name in the top bar; the Room tab shows the route
_STATUS_TEXT = (
    "$_state === 'live'"
    " ? 'Live' + ($_live_for ? ' · ' + $_live_for : '')"
    " : $_state === 'lost' ? 'Reconnecting…'"
    " : $_state === 'connecting' ? 'Connecting…'"
    " : $_state === 'pending' ? 'Needs approval'"
    " : $_state === 'removed' ? 'Removed'"
    " : 'Camera is off'"
)

_GLANCE_WORD = "$_glance === 'crying' ? 'Crying' : $_glance === 'stirring' ? 'Stirring' : 'Calm'"

# the picture view hides its dock while the picture plays; the glance view never does
_CHROME_OFF = "$_pic && !$_chrome && $_state === 'live' && !$_muted"

_MORE_TABS = (("picture", "Picture"), ("alerts", "Alerts"), ("room", "Room"))

# a screen that covers the page while it is not live
_COVER = (
    "absolute",
    "inset-0",
    "z-10",
    "flex",
    "flex-col",
    "items-center",
    "justify-center",
    "gap-4",
    "bg-ground",
    "p-6",
    "text-center",
)


def _meter(motion: bool = False, size: str = "") -> HtmlElement:
    """The segment meter. JS sets --level on this element only.

    Sound fills from the audio, movement from the camera's frame diff.
    """
    n = 24 if size == "wide" else 8
    return h.Div(
        {"data-motion-meter": True, "aria-label": "Movement"} if motion else {"data-meter": True},
        classes("meter", "meter-motion" if motion else "", f"meter-{size}" if size else ""),
        data.preserve_attr("style"),
        *[h.Span({"style": f"--i: {i}"}) for i in range(n)],
    )


def _room_row(label: str, *value) -> HtmlElement:
    return h.Div(
        classes("flex", "items-center", "justify-between", "gap-3", "py-2.5"),
        h.Span(classes("text-sm", "text-muted"), label),
        h.Span(classes("flex", "min-w-0", "items-center", "gap-1.5", "text-sm"), *value),
    )


def render_no_room(code: str, og_image: str) -> HtmlElement:
    return page(
        "No camera has this code · Philomena",
        og_image,
        h.Main(
            {"id": "watch"},
            classes(
                "mx-auto",
                "flex",
                "min-h-dvh",
                "w-full",
                "max-w-md",
                "flex-col",
                "items-center",
                "justify-center",
                "gap-4",
                "bg-ground",
                "p-6",
                "text-center",
            ),
            icons.video(classes("size-10", "text-accent")),
            h.H1(classes("text-2xl", "font-bold"), "No camera has this code"),
            h.P(classes("text-muted"), "Check the code on the camera phone."),
            h.A({"href": HOME.href()}, classes("btn", "btn-primary"), "Home"),
        ),
    )


def _glance() -> HtmlElement:
    """The glance view: one word, the line under it, and the two big meters."""
    return h.Div(
        {"data-part": "glance"},
        data.show("$_state === 'live'"),
        h.Div(
            classes("glance-hero"),
            h.P(
                {"role": "status", "aria-live": "polite", "data-glance-word": True},
                classes("glance-word"),
                data.text(_GLANCE_WORD),
            ),
            h.P(classes("glance-sub"), data.text("$_glance_sub")),
        ),
        h.Div(
            classes("flex", "flex-col", "gap-4"),
            # the sound row: the meter while sound plays, the button while it is off
            h.Button(
                {"type": "button"},
                classes("btn", "btn-primary", "btn-lg", "btn-block"),
                data.show("$_muted"),
                data.on("click", "app.sound.unlock(); app.rtc.setMuted(false)"),
                icons.volume(classes("size-5")),
                "Turn on sound",
            ),
            h.Div(
                data.show("!$_muted"),
                h.P(classes("glance-label"), icons.volume(classes("size-3.5")), "Sound"),
                _meter(size="wide"),
            ),
            h.Div(
                h.P(classes("glance-label"), icons.move(classes("size-3.5")), "Movement"),
                _meter(motion=True, size="wide"),
            ),
        ),
    )


def _more_sheet(spaced: str, others: list) -> HtmlElement:
    """More: three tabs of square tiles, so the sheet never scrolls."""
    return sheet(
        "_mdlg",
        "More",
        h.Div(
            {"role": "tablist"},
            classes("seg"),
            *[
                h.Button(
                    {"type": "button", "role": "tab"},
                    data.attr("aria-selected", f"$_mtab === '{key}' ? 'true' : 'false'"),
                    data.on("click", f"$_mtab = '{key}'"),
                    label,
                )
                for key, label in _MORE_TABS
            ],
        ),
        # every tab sits in the same cell: the sheet keeps the size of the tallest
        h.Div(
            classes("grid"),
            h.Div(
                {"role": "tabpanel"},
                classes("col-start-1", "row-start-1", "flex", "flex-col", "gap-3"),
                data.class_("invisible", "$_mtab !== 'picture'"),
                h.Div(
                    classes("grid", "grid-cols-4", "content-start", "gap-2"),
                    tile(
                        "Tonight",
                        "$_mdlg.close(); $_tloaded = false;"
                        " $_tdlg.showModal(); app.rtc.sendCtlAll({t: 'timeline?'})",
                        icons.activity(classes("size-6")),
                    ),
                    tile("Rotate", "$_wroot.view.rotate()", icons.rotate_cw(classes("size-6"))),
                    tile(
                        h.Span(data.text("$_fit === 'cover' ? 'Fit picture' : 'Fill screen'")),
                        "$_wroot.view.fit()",
                        h.Span(data.show("$_fit === 'contain'"), icons.maximize(classes("size-6"))),
                        h.Span(data.show("$_fit === 'cover'"), icons.minimize(classes("size-6"))),
                    ),
                    tile(
                        "Switch camera", "app.rtc.askFlip()", icons.switch_camera(classes("size-6"))
                    ),
                    tile(
                        "Sound only",
                        "$_sound_only = !$_sound_only; app.rtc.setVideo(!$_sound_only)",
                        icons.volume(classes("size-6")),
                        on="$_sound_only",
                    ),
                    tile(
                        "Brighten",
                        "$_bright = !$_bright;"
                        " localStorage.setItem('philomena.brighten.'"
                        " + $_wroot.dataset.code, $_bright ? '1' : '0')",
                        icons.sun(classes("size-6")),
                        on="$_bright",
                    ),
                    tile(
                        "Brighten on camera",
                        "$_brightcam = !$_brightcam;"
                        " app.rtc.sendCtlAll({t:'exposure', boost: $_brightcam})",
                        icons.sun(classes("size-6")),
                        on="$_brightcam",
                        show="$_cam_exposure",
                    ),
                ),
                look_switch(),
            ),
            h.Div(
                {"role": "tabpanel"},
                classes("col-start-1", "row-start-1", "flex", "flex-col", "gap-3"),
                data.class_("invisible", "$_mtab !== 'alerts'"),
                h.Div(
                    classes("grid", "grid-cols-4", "gap-2"),
                    tile(
                        h.Span(
                            data.text(
                                "$_push_hint === 'denied'"
                                " ? 'Notifications blocked' : 'Notify when locked'"
                            )
                        ),
                        "app.push.setOn($_push_hint !== 'on').then(v => $_push_hint = v)",
                        {"data-push-row": True},
                        # blocked is a state, not a switch: it looks out of reach
                        data.class_("opacity-50", "$_push_hint === 'denied'"),
                        icons.bell(classes("size-6")),
                        on="$_push_hint === 'on'",
                        show="!$_ios_hint",
                    ),
                    *[
                        tile(
                            label,
                            f"$_alerts.{key} = !$_alerts.{key};"
                            " localStorage.setItem('philomena.alerts',"
                            " JSON.stringify($_alerts));"
                            " app.sound.alerts($_alerts);"
                            " app.push.boot($_wroot).then(v => $_push_hint = v)",
                            icon(classes("size-6")),
                            on=f"$_alerts.{key}",
                        )
                        for key, icon, label in (
                            ("crying", icons.bell, "Crying"),
                            ("stirring", icons.activity, "Stirring"),
                            ("loud", icons.volume, "Loud sound"),
                            ("movement", icons.move, "Movement"),
                            ("lights", icons.sun, "Lights"),
                        )
                    ],
                ),
                h.P(
                    classes("text-xs", "text-muted"),
                    data.show("$_ios_hint"),
                    "Add Philomena to the Home Screen to get alerts when the phone is locked.",
                ),
                h.P(
                    classes("text-xs", "text-muted"),
                    data.show("!$_ios_hint"),
                    "This phone plays a sound for each alert that is on.",
                ),
            ),
            h.Div(
                {"role": "tabpanel"},
                classes("col-start-1", "row-start-1", "flex", "flex-col"),
                data.class_("invisible", "$_mtab !== 'room'"),
                h.Div(
                    classes("flex", "flex-col", "divide-y", "divide-line"),
                    _room_row("Code", h.Span(classes("font-mono", "tabular-nums"), spaced)),
                    _room_row(
                        "Connection",
                        icons.lock(classes("size-3.5", "text-muted")),
                        h.Span(
                            data.text(
                                "$_route === 'relay' ? 'Encrypted · via relay'"
                                " : $_route ? 'Encrypted · direct' : 'Not connected'"
                            )
                        ),
                    ),
                    h.Div(
                        data.show("$_cam_batt"),
                        _room_row(
                            "Camera battery",
                            h.Span(
                                data.text(
                                    "$_cam_batt ? Math.round($_cam_batt.level * 100) + '%'"
                                    " + ($_cam_batt.charging ? ' · charging' : '') : ''"
                                )
                            ),
                        ),
                    ),
                    h.Div(
                        data.show("$_last_event"),
                        _room_row(
                            "Last alert",
                            h.Span({"data-last-event": True}, data.text("$_last_event")),
                        ),
                    ),
                ),
                *(
                    [
                        h.Nav(
                            {"aria-label": "Other cameras"},
                            classes("list", "mt-3"),
                            h.P(classes("list-title"), "Other cameras"),
                            *[
                                h.A(
                                    {"href": f"/watch/{c[0]}"},
                                    h.Span(classes("status", "status-live" if c[2] else "")),
                                    h.Span(c[1] or f"Camera {c[0][:3]} {c[0][3:]}"),
                                )
                                for c in others
                            ],
                        )
                    ]
                    if others
                    else []
                ),
            ),
        ),
    )


def _tonight_sheet() -> HtmlElement:
    """Tonight: the camera's night history, asked for over the channel."""
    return sheet(
        "_tdlg",
        "Tonight",
        h.Div(
            classes("flex", "flex-col", "gap-1"),
            h.P(data.text("$_quiet_line"), data.show("$_quiet_line")),
            h.P(data.text("$_stirred_line"), data.show("$_stirred_line")),
            h.P(data.text("$_cried_line"), data.show("$_cried_line")),
            h.P(classes("text-muted"), data.show("!$_tloaded"), "Asking the camera…"),
            h.P(
                classes("text-muted"),
                data.show("$_tloaded && $_tcount === 0"),
                "Nothing recorded yet. The camera records while it runs.",
            ),
        ),
        h.Div(
            classes("h-[160px]", "w-full"),
            data.show("$_tloaded && $_tcount > 0"),
            h.Canvas({"data-chart": True}, classes("h-full", "w-full"), data.ignore_morph()),
        ),
        h.Div(
            {"role": "group", "aria-label": "Hours shown"},
            classes("seg", "self-end", "w-40"),
            data.show("$_tloaded && $_tcount > 0"),
            *[
                h.Button(
                    {"type": "button"},
                    data.attr("aria-pressed", f"$_thrs === {hrs} ? 'true' : 'false'"),
                    data.on(
                        "click",
                        f"$_thrs = {hrs}; app.nightChart.draw("
                        "$_tdlg.querySelector('canvas'),"
                        f" $_tdlg._titems || [], {hrs})",
                    ),
                    f"{hrs} h",
                )
                for hrs in (12, 24)
            ],
        ),
        on=({"id": "tonight"},),
    )


def render(
    code: str,
    tab: str,
    name: str,
    og_image: str,
    vapid: str,
    cam_name: str = "",
    cams: list | None = None,
) -> HtmlElement:
    spaced = f"{code[:3]} {code[3:]}"
    others = [c for c in (cams or []) if c[0] != code]
    return page(
        f"Watching {code} · Philomena",
        og_image,
        h.Main(
            {
                "id": "watch",
                "data-role": "watch",
                "data-code": code,
                "data-vapid": vapid,
                "data-tab": tab,
                "data-idle": "4000",
                "data-mode": "glance",
                "data-glance": "calm",
            },
            classes("relative", "h-dvh", "w-full", "overflow-hidden", "bg-ground"),
            data.ref("_wroot"),
            data.signals(
                {
                    "tab": tab,
                    "name": name,
                    "_state": "waiting",
                    "_muted": True,
                    "_wake": True,
                    "_route": "",
                    "_chrome": True,
                    "_alarm": False,
                    "_dim": False,
                    "_seen_live": False,
                    "_install_gone": False,
                    "_fit": "contain",
                    "_talking": False,
                    "_sound_only": False,
                    "_cam_batt": None,
                    "_live_for": "",
                    "_alerts": {},
                    "_event_banner": "",
                    "_last_event": "",
                    "_quiet_line": "",
                    "_stirred_line": "",
                    "_cried_line": "",
                    "_tloaded": False,
                    "_tcount": 0,
                    "_thrs": 12,
                    "_push": "",
                    "_push_hint": "",
                    "_cam_name": cam_name,
                    "_cam_exposure": False,
                    "_bright": False,
                    "_brightcam": False,
                    "_mtab": "picture",
                    "_pic": False,
                    "_glance": "calm",
                    "_glance_sub": "",
                    "_wake_gone": False,
                },
                if_missing=True,
            ),
            data.attr("data-mode", "$_pic ? 'picture' : 'glance'"),
            data.attr("data-glance", "$_glance"),
            data.init(
                f"{at.get(WATCH_LIVE.href(code), retry='always')};"
                " el.glance ??= app.glance((k, line) => { $_glance = k; $_glance_sub = line });"
                " app.rtc.start(el, {"
                "state: v => {"
                " $_state = v;"
                " if (v === 'live') $_seen_live = true;"
                " app.sound.state(v);"
                " },"
                "muted: v => $_muted = v,"
                "route: v => $_route = v,"
                "talking: v => $_talking = v,"
                "battery: v => $_cam_batt = v,"
                "liveFor: v => $_live_for = v,"
                "toast: t => $_toast = t,"
                "event: e => { app.sound.event(e); el.glance.event(e) },"
                "events: items => { app.sound.events(items); el.glance.events(items) },"
                "timeline: items => {"
                " $_tloaded = true; $_tcount = items.length; $_thrs = 12;"
                " app.nightChart.show($_tdlg, items, s => {"
                "  $_quiet_line = s.quiet; $_stirred_line = s.stirred;"
                "  $_cried_line = s.cried;"
                " });"
                " },"
                "name: v => $_cam_name = v,"
                "exposure: v => $_cam_exposure = v"
                "});"
                " app.wake.start(v => $_wake = v);"
                " el.idle ??= app.idle(el, v => $_chrome = v);"
                " el.view ??= app.view(el.querySelector('[data-view]'), v => $_fit = v);"
                " el.sound ??= app.sound.wire(el, {"
                "alarm: v => $_alarm = v,"
                "wake: () => $_dim = false,"
                "toast: t => $_toast = t,"
                "muted: () => $_muted,"
                "dim: () => $_dim,"
                "event: label => $_event_banner = label,"
                "lastEvent: t => $_last_event = t"
                "});"
                " $_alerts = Object.assign("
                "  {crying:true,stirring:true,loud:false,movement:false,lights:false},"
                "  JSON.parse(localStorage.getItem('philomena.alerts') || '{}'));"
                " app.sound.alerts($_alerts);"
                " app.push.boot(el).then(v => $_push_hint = v);"
                " $_pic = localStorage.getItem('philomena.mode') === 'picture';"
                " $_bright = localStorage.getItem('philomena.brighten.'"
                " + el.dataset.code) === '1'"
            ),
            data.effect(
                "el.idle && el.idle.poke($_state, $_muted);"
                " app.rtc.setLooking?.("
                "document.visibilityState === 'visible' && !$_dim && !$_sound_only)"
            ),
            data.on("pointerdown", "el.idle && el.idle.poke()"),
            data.on(
                "visibilitychange",
                "app.wake.visible();"
                " app.rtc.setLooking?.("
                "document.visibilityState === 'visible' && !$_dim && !$_sound_only);"
                " document.visibilityState === 'hidden'"
                " ? app.sound.hidden()"
                " : app.sound.visible()",
                target="document",
            ),
            # the picture: the whole screen in the picture view, a strip in the glance view
            h.Div(
                {"data-frame": True},
                classes("absolute", "inset-0"),
                h.Div(
                    {"data-view": True, "data-code": code},
                    classes("absolute", "inset-0", "h-full", "w-full"),
                    data.preserve_attr("style"),
                    data.preserve_attr("data-fit"),
                    h.Video(
                        {
                            "data-rtc": "remote",
                            "autoplay": True,
                            "playsinline": True,
                            "muted": True,
                        },
                        classes("absolute", "inset-0", "h-full", "w-full", "object-contain"),
                        data.class_("video-bright", "$_bright"),
                    ),
                ),
                h.Button(
                    {"type": "button", "data-part": "show-pic"},
                    data.on(
                        "click", "$_pic = true; localStorage.setItem('philomena.mode', 'picture')"
                    ),
                    icons.eye(classes("size-4")),
                    h.Span(data.text("$_sound_only ? 'Picture off · sound only' : 'Show picture'")),
                ),
            ),
            # sound only, in the picture view: the icon and the meters keep the feed alive
            h.Div(
                classes(*_COVER),
                data.show("$_sound_only && $_pic"),
                icons.volume(classes("size-10", "text-accent")),
                h.P(classes("text-lg", "font-bold"), "Sound only"),
                h.P(classes("text-sm", "text-muted"), "The video is off. The sound stays on."),
            ),
            # not live: one icon and one gentle line
            h.Div(
                {"role": "status"},
                classes(*_COVER),
                data.show("$_state !== 'live' && $_state !== 'pending'"),
                h.Span(
                    data.show("$_state !== 'connecting' && $_state !== 'lost'"),
                    icons.video(classes("size-10", "text-accent")),
                ),
                h.Span(
                    classes("spinner", "text-accent"),
                    data.show("$_state === 'connecting' || $_state === 'lost'"),
                ),
                h.P(classes("text-xl", "font-bold"), data.text(_WAITING_TEXT)),
                h.P(
                    classes("text-sm", "text-muted"), "Keep this page open. It connects on its own."
                ),
            ),
            # waiting for the camera phone's approval
            h.Div(
                {"role": "status"},
                classes(*_COVER),
                data.show("$_state === 'pending'"),
                icons.eye(classes("size-10", "text-accent")),
                h.P(classes("text-xl", "font-bold"), "Almost there"),
                h.P(
                    classes("text-sm", "text-muted"),
                    "Ask for the camera phone to approve this phone.",
                ),
                h.Form(
                    classes("join", "w-full", "max-w-xs"),
                    data.on("submit", at.post(WATCH_NAME.href(code))),
                    h.Input(
                        {
                            "type": "text",
                            "maxlength": 30,
                            "aria-label": "Your name",
                            "placeholder": "Your name",
                        },
                        classes("input", "min-w-0", "flex-1"),
                        data.bind("name"),
                    ),
                    h.Button({"type": "submit"}, classes("btn", "btn-primary"), "Save"),
                ),
                h.P(classes("text-xs", "text-muted"), "Your name, so the camera knows you."),
            ),
            # the camera phone removed this phone
            h.Div(
                {"role": "alert"},
                classes(*_COVER, "z-40"),
                data.show("$_state === 'removed'"),
                icons.eye(classes("size-10", "text-accent")),
                h.H1(classes("text-2xl", "font-bold"), "Removed"),
                h.P(classes("text-muted"), "The camera phone removed this phone."),
                h.A({"href": HOME.href()}, classes("btn", "btn-primary"), "Home"),
            ),
            top_bar(
                "app.rtc.leave()",
                f"$_cam_name || 'Camera {spaced}'",
                _STATUS_TEXT,
                {
                    "status-live": "$_state === 'live'",
                    "animate-pulse": "$_state === 'live'",
                    "status-alarm": "$_state === 'lost'",
                    "status-warn": "$_state === 'pending'",
                },
                # the picture view keeps the meters in its top bar: the bar does not hide
                end=(
                    h.Div(
                        classes("flex", "shrink-0", "items-center", "gap-1.5", "pr-2"),
                        data.show("$_state === 'live' && $_pic"),
                        icons.volume(classes("size-3.5", "text-muted")),
                        _meter(),
                        icons.move(classes("ml-1.5", "size-3.5", "text-muted")),
                        _meter(motion=True),
                    ),
                ),
            ),
            # under the top bar: one event, then what needs a hand
            h.Div(
                {"data-part": "alerts"},
                classes(
                    "absolute",
                    "inset-x-3",
                    "top-[calc(4.25rem+env(safe-area-inset-top))]",
                    "z-30",
                    "flex",
                    "flex-col",
                    "gap-2",
                ),
                # the glance word says it already; the picture view needs the line
                h.Div(
                    {"role": "alert", "data-event-banner": True},
                    classes("alert", "shadow-lg"),
                    data.show("$_event_banner && $_pic"),
                    data.class_("alert-alarm", "$_event_banner.indexOf('Crying') === 0"),
                    h.Span(classes("font-semibold"), data.text("$_event_banner")),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-sm"),
                        data.on("click", "$_event_banner = ''"),
                        "Dismiss",
                    ),
                ),
                h.Div(
                    {"role": "alert"},
                    classes("alert", "alert-alarm", "shadow-lg"),
                    data.show("$_alarm"),
                    h.Span("No connection to the camera"),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-sm"),
                        data.on("click", "$_wroot.sound.silence()"),
                        "Silence",
                    ),
                ),
                h.Div(
                    {"role": "status"},
                    classes("alert", "alert-warn", "text-sm"),
                    data.show("$_cam_batt && $_cam_batt.level <= 0.3"),
                    h.Span(
                        data.text(
                            "$_cam_batt ? 'Camera battery '"
                            " + Math.round($_cam_batt.level * 100) + '%. Plug it in.' : ''"
                        )
                    ),
                ),
                h.Div(
                    {"role": "status"},
                    classes("alert", "alert-warn", "text-sm"),
                    data.show("!$_wake && !$_wake_gone"),
                    h.Span("Turn off auto-lock so the screen stays on."),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-sm", "btn-ghost"),
                        data.on("click", "$_wake_gone = true"),
                        "Dismiss",
                    ),
                ),
                # the install hint, once, after the first live picture
                h.Div(
                    {"role": "status"},
                    classes("alert", "text-sm"),
                    data.show("($_installable || $_ios_hint) && $_seen_live && !$_install_gone"),
                    h.Span(
                        data.text(
                            "$_installable ? 'Install Philomena for alerts on a locked phone.'"
                            " : 'Add to Home Screen: tap Share, then Add to Home Screen.'"
                        )
                    ),
                    h.Div(
                        classes("flex", "gap-1"),
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
                ),
            ),
            _glance(),
            # in the thumb's reach: sound, while it is off
            h.Button(
                {"type": "button", "data-part": "cta"},
                classes(
                    "btn",
                    "btn-primary",
                    "btn-lg",
                    "absolute",
                    "inset-x-3",
                    "bottom-[calc(5rem+env(safe-area-inset-bottom))]",
                    "z-20",
                    "shadow-lg",
                ),
                data.show("$_state === 'live' && $_muted"),
                data.on("click", "app.sound.unlock(); app.rtc.setMuted(false)"),
                icons.volume(classes("size-5")),
                "Turn on sound",
            ),
            # the viewer's dim screen: one line and the big meters
            h.Div(
                {"role": "button", "aria-label": "Wake the screen"},
                classes(
                    "lights-out",
                    "fixed",
                    "inset-0",
                    "z-[60]",
                    "flex",
                    "flex-col",
                    "items-center",
                    "justify-center",
                    "gap-6",
                    "bg-ground",
                    "text-muted",
                ),
                data.show("$_dim"),
                data.on("click", "$_dim = false"),
                h.Div(
                    classes("flex", "items-center", "gap-2", "text-sm"),
                    h.Span(
                        classes("status", "status-live", "motion-reduce:animate-none"),
                        data.class_("animate-pulse", "$_state === 'live'"),
                    ),
                    h.Span(data.text(_LIVE_TEXT)),
                ),
                h.Div(
                    classes("flex", "items-end", "gap-4"),
                    _meter(size="lg"),
                    _meter(motion=True, size="lg"),
                ),
            ),
            h.Div(
                {"data-part": "dock"},
                classes("dock", "z-30", "transition-opacity", "duration-300"),
                data.classes({"opacity-0": _CHROME_OFF, "pointer-events-none": _CHROME_OFF}),
                h.Button(
                    {"type": "button"},
                    data.attr("disabled", "$_state === 'pending' || $_state === 'removed'"),
                    data.attr("aria-pressed", "$_muted ? 'false' : 'true'"),
                    data.class_("dock-active", "!$_muted"),
                    data.on("click", "app.sound.unlock(); app.rtc.setMuted(!$_muted)"),
                    h.Span(data.show("$_muted"), icons.volume_x(classes("size-6"))),
                    h.Span(data.show("!$_muted"), icons.volume(classes("size-6"))),
                    h.Span(classes("dock-label"), "Sound"),
                ),
                h.Button(
                    {"type": "button"},
                    classes("touch-none"),
                    data.attr("disabled", "$_state !== 'live'"),
                    data.class_("dock-active", "$_talking"),
                    data.on("pointerdown", "app.rtc.talkStart()"),
                    data.on("pointerup", "app.rtc.talkEnd()"),
                    data.on("pointercancel", "app.rtc.talkEnd()"),
                    data.on("pointerleave", "app.rtc.talkEnd()"),
                    data.on("contextmenu", "evt.preventDefault()"),
                    icons.mic(classes("size-6")),
                    h.Span(classes("dock-label"), data.text("$_talking ? 'Talking…' : 'Talk'")),
                ),
                h.Button(
                    {"type": "button"},
                    data.on(
                        "click",
                        "$_pic = !$_pic;"
                        " localStorage.setItem('philomena.mode', $_pic ? 'picture' : 'glance')",
                    ),
                    h.Span(data.show("!$_pic"), icons.eye(classes("size-6"))),
                    h.Span(data.show("$_pic"), icons.activity(classes("size-6"))),
                    h.Span(classes("dock-label"), data.text("$_pic ? 'Glance' : 'Picture'")),
                ),
                h.Button(
                    {"type": "button"},
                    data.on("click", "$_dim = true"),
                    icons.moon(classes("size-6")),
                    h.Span(classes("dock-label"), "Screen off"),
                ),
                h.Button(
                    {"type": "button"},
                    data.on("click", "$_mdlg.showModal()"),
                    icons.ellipsis(classes("size-6")),
                    h.Span(classes("dock-label"), "More"),
                ),
            ),
            _more_sheet(spaced, others),
            _tonight_sheet(),
        ),
    )
