import io

import segno
from stario import h
from stario.datastar import at, data
from stario.markup import HtmlElement, SafeString, classes

from app.common import icons
from app.common.shell import page
from app.common.ui import look_switch, sheet, top_bar
from app.features.cam.urls import (
    CAM,
    CAM_APPROVE,
    CAM_LIVE,
    CAM_NAME,
    CAM_NEW_CODE,
    CAM_REMOVE,
)
from app.features.home.urls import HOME
from app.features.watch.urls import WATCH_ROOM
from app.rooms.data import Approval


def render_forbidden(og_image: str) -> HtmlElement:
    return page(
        "This camera belongs to another phone · Philomena",
        og_image,
        h.Main(
            {"id": "cam"},
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
            icons.lock(classes("size-10", "text-accent")),
            h.H1(
                classes("text-2xl", "font-bold"),
                "This camera belongs to another phone",
            ),
            h.A({"href": HOME.href()}, classes("btn", "btn-primary"), "Home"),
        ),
    )


def render_knocks(approvals: list[Approval], code: str) -> HtmlElement:
    """The visible pending cards; patched as `#viewers` whenever the panel changes."""
    return h.Div(
        {"id": "viewers"},
        classes("flex", "flex-col", "gap-2"),
        *[
            h.Div(
                {"role": "alert"},
                classes("alert", "shadow-lg"),
                h.P(
                    classes("min-w-0", "font-medium"),
                    f"{a.name or 'A phone'} wants to watch",
                ),
                h.Div(
                    classes("flex", "gap-2"),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-ghost", "btn-sm"),
                        data.on("click", at.post(CAM_REMOVE.href(code, a.device_id))),
                        "Not now",
                    ),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-primary", "btn-sm"),
                        data.on("click", at.post(CAM_APPROVE.href(code, a.device_id))),
                        "Allow",
                    ),
                ),
            )
            for a in approvals
            if a.status == "pending"
        ],
    )


def render_viewers(approvals: list[Approval], online: set[str], code: str) -> HtmlElement:
    """The device rows inside the viewers sheet; patched as `#viewer-list`."""
    rows: list[HtmlElement] = []
    for a in approvals:
        pending = a.status == "pending"
        watching = a.device_id in online
        name = a.name or "A phone"
        rows.append(
            h.Div(
                classes("flex", "items-center", "gap-3", "py-3"),
                h.Span(
                    classes(
                        "status",
                        "shrink-0",
                        "status-warn" if pending else "status-live" if watching else "",
                    ),
                ),
                h.Div(
                    classes("flex", "min-w-0", "flex-1", "flex-col"),
                    h.P(classes("truncate", "font-medium"), name),
                    h.P(
                        classes("text-xs", "text-muted"),
                        "Wants to watch"
                        if pending
                        else "Watching now"
                        if watching
                        else "Allowed · not watching",
                    ),
                ),
                h.Div(
                    classes("flex", "shrink-0", "items-center", "gap-1"),
                    data.show(f"$_removing !== '{a.device_id}'"),
                    *(
                        [
                            h.Button(
                                {"type": "button"},
                                classes("btn", "btn-primary", "btn-sm"),
                                data.on("click", at.post(CAM_APPROVE.href(code, a.device_id))),
                                "Allow",
                            )
                        ]
                        if pending
                        else []
                    ),
                    h.Button(
                        {"type": "button", "aria-label": f"Remove {name}"},
                        classes("btn", "btn-ghost", "btn-sm", "btn-square"),
                        data.on("click", f"$_removing = '{a.device_id}'"),
                        icons.x(classes("size-4")),
                    ),
                ),
                h.Div(
                    classes("flex", "shrink-0", "items-center", "gap-1"),
                    data.show(f"$_removing === '{a.device_id}'"),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-ghost", "btn-sm"),
                        data.on("click", "$_removing = ''"),
                        "Keep",
                    ),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-alarm", "btn-sm"),
                        data.on(
                            "click",
                            f"{at.post(CAM_REMOVE.href(code, a.device_id))}; $_removing = ''",
                        ),
                        "Remove",
                    ),
                ),
            )
        )
    return h.Div(
        {"id": "viewer-list"},
        classes("flex", "flex-col", "divide-y", "divide-line"),
        *(
            rows
            or [
                h.Div(
                    classes("flex", "flex-col", "items-center", "gap-3", "py-4", "text-center"),
                    h.P(classes("text-sm", "text-muted"), "No phone may watch yet."),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-primary", "gap-2"),
                        data.on("click", "$_vdlg.close(); $_pairdlg.showModal()"),
                        icons.user_plus(classes("size-4")),
                        "Invite a phone",
                    ),
                )
            ]
        ),
    )


def qr_svg(url: str) -> str:
    buf = io.BytesIO()
    segno.make(url).save(
        buf,
        kind="svg",
        scale=8,
        border=2,
        dark="#000000",
        light="#ffffff",
        xmldecl=False,
        svgclass="block h-auto w-full",
        omitsize=True,
        nl=False,
    )
    return buf.getvalue().decode().replace("<svg ", '<svg shape-rendering="crispEdges" ', 1)


def render(
    code: str,
    tab: str,
    approvals: list[Approval],
    online: set[str],
    url: str | None,
    og_image: str,
    room_name: str,
) -> HtmlElement:
    spaced = f"{code[:3]} {code[3:]}"
    link = url or WATCH_ROOM.href(code)
    return page(
        f"Camera {code} · Philomena",
        og_image,
        h.Main(
            {
                "id": "cam",
                "data-role": "cam",
                "data-code": code,
                "data-tab": tab,
                "data-lights-out": "15",
                "data-redim": "30",
            },
            classes("relative", "h-dvh", "w-full", "overflow-hidden", "bg-ground"),
            data.ref("_camroot"),
            data.on("pagehide", "app.rtc.timeline?.flush()", target="window"),
            data.signals(
                {
                    "tab": tab,
                    "_state": "connecting",
                    "_viewers": 0,
                    "_dim": False,
                    "_dim_in": 0,
                    "_wake": True,
                    "_route": "",
                    "_copied": False,
                    "_pending": sum(a.status == "pending" for a in approvals),
                    "_removing": "",
                    "_newcode": False,
                    "_clrhist": False,
                    "_leaving": False,
                    "_camname": room_name,
                    "_talking": False,
                    "_talk_blocked": False,
                    "_detect_blocked": False,
                    "_batt_low": False,
                    "_live_for": "",
                    "_wake_gone": False,
                },
                if_missing=True,
            ),
            data.init(
                f"{at.get(CAM_LIVE.href(code), retry='always')};"
                " app.rtc.start(el, {"
                "state: v => $_state = v,"
                "viewers: v => $_viewers = v,"
                "route: v => $_route = v,"
                "battery: v => $_batt_low = (v.level <= 0.2 && !v.charging),"
                "talking: v => $_talking = v,"
                "talkBlocked: v => $_talk_blocked = v,"
                "detectBlocked: v => $_detect_blocked = v,"
                "liveFor: v => $_live_for = v"
                "});"
                " app.wake.start(v => $_wake = v);"
                " el.night ??= app.night(el, v => $_dim = v, s => $_dim_in = s)"
            ),
            data.effect("el.night && el.night.viewers($_viewers)"),
            data.on("visibilitychange", "app.wake.visible()", target="document"),
            h.Video(
                {
                    "data-rtc": "preview",
                    "muted": True,
                    "playsinline": True,
                    "autoplay": True,
                },
                classes("absolute", "inset-0", "h-full", "w-full", "object-cover"),
            ),
            # a viewer's talk-back mic replays through this element
            h.Audio(
                {"data-rtc": "talk", "autoplay": True},
                data.ignore_morph(),
            ),
            top_bar(
                "$_leaving = true",
                "$_camname || 'Camera'",
                "$_state === 'lost' ? 'Reconnecting…'"
                " : $_state === 'denied' ? 'Blocked'"
                " : $_state === 'replaced' ? 'Moved'"
                " : $_state === 'connecting' ? 'Starting…'"
                " : $_viewers > 0 ? $_viewers + ' watching'"
                " + ($_route === 'relay' ? ' · via relay' : '')"
                " : 'Nobody watching'",
                {
                    "status-live": "$_state === 'live' && $_viewers > 0",
                    "animate-pulse": "$_state === 'live' && $_viewers > 0",
                    "status-alarm": (
                        "$_state === 'lost' || $_state === 'replaced' || $_state === 'denied'"
                    ),
                },
            ),
            # under the top bar: what needs a hand
            h.Div(
                classes(
                    "absolute",
                    "inset-x-3",
                    "top-[calc(4.25rem+env(safe-area-inset-top))]",
                    "z-30",
                    "flex",
                    "flex-col",
                    "gap-2",
                ),
                h.Div(
                    {"role": "status"},
                    classes("alert", "text-sm"),
                    data.show("$_talking"),
                    h.Span(
                        classes("flex", "items-center", "gap-2"),
                        icons.mic(classes("size-4")),
                        "Talking",
                    ),
                ),
                h.Button(
                    {"type": "button"},
                    classes("alert", "alert-warn", "text-sm"),
                    data.show("$_talk_blocked || $_detect_blocked"),
                    data.on("click", "app.detect.resume()"),
                    h.Span(
                        data.text(
                            "$_detect_blocked"
                            " ? 'Tap to turn on sound alerts'"
                            " : 'Tap to allow talk-back'"
                        )
                    ),
                ),
                h.Div(
                    {"role": "status"},
                    classes("alert", "alert-warn", "text-sm"),
                    data.show("$_batt_low"),
                    h.Span("Plug in this phone."),
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
            ),
            # above the dock: leave, the countdown, and the knock cards
            h.Div(
                classes(
                    "absolute",
                    "inset-x-3",
                    "bottom-[calc(5rem+env(safe-area-inset-bottom))]",
                    "z-20",
                    "flex",
                    "max-h-[calc(100dvh-11rem)]",
                    "flex-col",
                    "justify-end",
                    "gap-2",
                    "overflow-y-auto",
                ),
                h.Div(
                    {"role": "alert"},
                    classes("alert", "shadow-lg"),
                    data.show("$_leaving"),
                    h.Div(
                        h.P(classes("font-medium"), "Stop the camera?"),
                        h.P(classes("text-sm", "text-muted"), "Viewers lose the picture."),
                    ),
                    h.Div(
                        classes("flex", "gap-2"),
                        h.Button(
                            {"type": "button"},
                            classes("btn", "btn-ghost", "btn-sm"),
                            data.on("click", "$_leaving = false"),
                            "Keep on",
                        ),
                        h.Button(
                            {"type": "button"},
                            classes("btn", "btn-alarm", "btn-sm"),
                            data.on("click", "app.rtc.leave()"),
                            "Stop",
                        ),
                    ),
                ),
                h.Div(
                    classes("alert", "shadow-lg"),
                    data.show("$_dim_in > 0"),
                    h.Span(data.text("'Lights out in ' + $_dim_in + ' s'")),
                    h.Button(
                        {"type": "button"},
                        classes("btn", "btn-sm", "btn-primary"),
                        data.on("click", "$_camroot.night.keep()"),
                        "Keep on",
                    ),
                ),
                render_knocks(approvals, code),
            ),
            # lights-out: a black screen, one dim line, low on the phone
            h.Div(
                {"role": "button", "aria-label": "Wake the screen"},
                classes(
                    "lights-out",
                    "fixed",
                    "inset-0",
                    "z-50",
                    "flex",
                    "items-end",
                    "justify-center",
                    "bg-black",
                    "pb-[33vh]",
                    "text-muted",
                ),
                data.show("$_dim"),
                data.on("click", "$_camroot.night.out()"),
                h.Div(
                    classes("flex", "items-center", "gap-2", "text-sm"),
                    h.Span(
                        classes("status", "status-live", "motion-reduce:animate-none"),
                        data.class_("animate-pulse", "$_viewers > 0"),
                    ),
                    h.Span(
                        data.text(
                            "$_viewers > 0"
                            " ? 'Camera on · ' + $_viewers + ' watching'"
                            " : 'Camera on · waiting'"
                        )
                    ),
                ),
            ),
            h.Div(
                classes("dock", "z-30"),
                h.Button(
                    {"type": "button"},
                    data.on("click", "$_pairdlg.showModal()"),
                    icons.user_plus(classes("size-6")),
                    h.Span(classes("dock-label"), "Invite"),
                ),
                h.Button(
                    {"type": "button"},
                    data.on("click", "$_vdlg.showModal()"),
                    h.Span(
                        classes("relative"),
                        h.Span(
                            classes("badge", "absolute", "-top-1.5", "-right-2.5"),
                            data.show("$_pending > 0"),
                            data.text("$_pending"),
                        ),
                        icons.users(classes("size-6")),
                    ),
                    h.Span(
                        classes("dock-label"),
                        data.text("$_viewers > 0 ? 'Viewers · ' + $_viewers : 'Viewers'"),
                    ),
                ),
                h.Button(
                    {"type": "button"},
                    data.on("click", "app.rtc.flip()"),
                    icons.switch_camera(classes("size-6")),
                    h.Span(classes("dock-label"), "Flip"),
                ),
                h.Button(
                    {"type": "button"},
                    data.on("click", "$_camroot.night.dim()"),
                    icons.moon(classes("size-6")),
                    h.Span(classes("dock-label"), "Lights out"),
                ),
                h.Button(
                    {"type": "button"},
                    data.on("click", "$_sdlg.showModal()"),
                    icons.sliders(classes("size-6")),
                    h.Span(classes("dock-label"), "Settings"),
                ),
            ),
            # Invite: the QR, the code, and two ways to send the link
            sheet(
                "_pairdlg",
                "Invite a phone",
                *(
                    [
                        h.Div(
                            {
                                "aria-label": f"QR code for {url}",
                                "data-url": url,
                                "role": "img",
                            },
                            classes(
                                "mx-auto",
                                "w-44",
                                "rounded-box",
                                "bg-white",
                                "p-2",
                            ),
                            SafeString(qr_svg(url)),
                        )
                    ]
                    if url
                    else []
                ),
                h.Div(
                    classes("flex", "flex-col", "items-center", "gap-1", "text-center"),
                    h.P(
                        {"data-digits": True},
                        classes("font-mono", "text-4xl", "tabular-nums", "tracking-wider"),
                        spaced,
                    ),
                    h.P(
                        classes("text-sm", "text-muted"),
                        "Scan the code or open the link on the other phone.",
                    ),
                ),
                h.Div(
                    classes("grid", "grid-cols-2", "gap-2"),
                    h.Button(
                        {"type": "button", "data-copy": link},
                        classes("btn", "gap-2"),
                        data.on("click", "app.share.copyLink(el.dataset.copy, v => $_copied = v)"),
                        icons.copy(classes("size-4")),
                        h.Span(data.text("$_copied === 'copied' ? 'Copied' : 'Copy link'")),
                    ),
                    h.Button(
                        {"type": "button", "data-share": link},
                        classes("btn", "btn-primary", "gap-2"),
                        data.on("click", "app.share.send(el.dataset.share, v => $_copied = v)"),
                        icons.share(classes("size-4")),
                        h.Span(data.text("$_copied === 'shared' ? 'Shared' : 'Share'")),
                    ),
                ),
                on=(
                    data.init("$_viewers === 0 && $_pending === 0 && !el.open && el.showModal()"),
                    data.effect("($_viewers > 0 || $_pending > 0) && el.close()"),
                ),
            ),
            # Viewers: the phones that may watch, and nothing else
            sheet(
                "_vdlg",
                "Viewers",
                render_viewers(approvals, online, code),
            ),
            # Settings: the name, the code, and the night history
            sheet(
                "_sdlg",
                "Camera settings",
                h.Div(
                    classes("flex", "flex-col", "divide-y", "divide-line"),
                    h.Form(
                        classes("flex", "flex-col", "gap-2", "pb-4"),
                        data.on(
                            "submit",
                            f"fetch('{CAM_NAME.href(code)}',"
                            " {method: 'POST',"
                            "  headers: {'content-type': 'application/json'},"
                            "  body: JSON.stringify({name: $_camname})})"
                            ".then(r => $_toast = r.ok ? 'Name saved' : 'Could not save the name')",
                        ),
                        h.Label(classes("text-sm", "text-muted"), {"for": "camname"}, "Name"),
                        h.Div(
                            classes("join", "w-full"),
                            h.Input(
                                {
                                    "id": "camname",
                                    "type": "text",
                                    "maxlength": "30",
                                    "placeholder": "Nursery",
                                },
                                classes("input", "min-w-0", "flex-1"),
                                data.bind("_camname"),
                            ),
                            h.Button(
                                {"type": "submit"},
                                classes("btn"),
                                "Save",
                            ),
                        ),
                    ),
                    h.Div(
                        classes("flex", "flex-col", "gap-2", "py-3"),
                        h.Div(
                            classes("flex", "items-center", "justify-between", "gap-2"),
                            h.Div(
                                h.P(classes("text-sm", "text-muted"), "Code"),
                                h.P(classes("font-mono", "tabular-nums"), spaced),
                            ),
                            h.Button(
                                {"type": "button"},
                                classes("btn", "btn-sm"),
                                data.show("!$_newcode"),
                                data.on("click", "$_newcode = true"),
                                "New code",
                            ),
                        ),
                        h.Div(
                            classes("flex", "items-center", "justify-between", "gap-2"),
                            data.show("$_newcode"),
                            h.P(
                                classes("text-sm", "text-muted"),
                                "Every viewer must be allowed again.",
                            ),
                            h.Div(
                                classes("flex", "shrink-0", "gap-2"),
                                h.Button(
                                    {"type": "button"},
                                    classes("btn", "btn-ghost", "btn-sm"),
                                    data.on("click", "$_newcode = false"),
                                    "Keep",
                                ),
                                h.Button(
                                    {"type": "button"},
                                    classes("btn", "btn-primary", "btn-sm"),
                                    data.on("click", at.post(CAM_NEW_CODE.href(code))),
                                    "New code",
                                ),
                            ),
                        ),
                    ),
                    h.Div(
                        classes("flex", "flex-col", "gap-2", "pt-3"),
                        h.Div(
                            classes("flex", "items-center", "justify-between", "gap-2"),
                            h.Div(
                                h.P(classes("text-sm", "text-muted"), "Night history"),
                                h.P(classes("text-sm"), "Kept on this phone"),
                            ),
                            h.Button(
                                {"type": "button"},
                                classes("btn", "btn-sm", "btn-ghost", "text-alarm"),
                                data.show("!$_clrhist"),
                                data.on("click", "$_clrhist = true"),
                                "Clear",
                            ),
                        ),
                        h.Div(
                            classes("flex", "items-center", "justify-between", "gap-2"),
                            data.show("$_clrhist"),
                            h.P(classes("text-sm", "text-muted"), "Viewers lose tonight's chart."),
                            h.Div(
                                classes("flex", "shrink-0", "gap-2"),
                                h.Button(
                                    {"type": "button"},
                                    classes("btn", "btn-ghost", "btn-sm"),
                                    data.on("click", "$_clrhist = false"),
                                    "Keep",
                                ),
                                h.Button(
                                    {"type": "button"},
                                    classes("btn", "btn-alarm", "btn-sm"),
                                    data.on("click", "app.rtc.timeline.clear(); $_clrhist = false"),
                                    "Clear",
                                ),
                            ),
                        ),
                    ),
                ),
                h.Div(
                    classes("flex", "flex-col", "gap-2", "border-t", "border-line", "pt-3"),
                    h.P(classes("text-sm", "text-muted"), "Look"),
                    look_switch(),
                ),
            ),
            # replaced / denied full screens
            h.Div(
                {"role": "alert"},
                classes(
                    "fixed",
                    "inset-0",
                    "z-40",
                    "flex",
                    "flex-col",
                    "items-center",
                    "justify-center",
                    "gap-4",
                    "bg-ground",
                    "p-6",
                    "text-center",
                ),
                data.show("$_state === 'replaced'"),
                icons.video(classes("size-10", "text-accent")),
                h.H1(classes("text-2xl", "font-bold"), "This camera moved"),
                h.P(
                    classes("text-muted"),
                    "Another device is now the camera for this code.",
                ),
                h.A({"href": HOME.href()}, classes("btn", "btn-primary"), "Back"),
            ),
            h.Div(
                {"role": "alert"},
                classes(
                    "fixed",
                    "inset-0",
                    "z-40",
                    "flex",
                    "flex-col",
                    "items-center",
                    "justify-center",
                    "gap-4",
                    "bg-ground",
                    "p-6",
                    "text-center",
                ),
                data.show("$_state === 'denied'"),
                icons.video(classes("size-10", "text-accent")),
                h.H1(classes("text-2xl", "font-bold"), "Camera blocked"),
                h.P(
                    classes("text-muted"),
                    "Allow camera and microphone access, then reload.",
                ),
                h.A({"href": CAM.href(code)}, classes("btn", "btn-primary"), "Reload"),
            ),
        ),
    )
