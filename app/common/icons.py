"""Inline SVG icons. Shapes from Lucide (https://lucide.dev), ISC License."""

from stario.markup import svg
from stario.markup.types import HtmlElement

_BASE = {
    "xmlns": "http://www.w3.org/2000/svg",
    "width": "24",
    "height": "24",
    "viewBox": "0 0 24 24",
    "fill": "none",
    "stroke": "currentColor",
    "stroke-width": "1.75",
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
    "aria-hidden": "true",
}


def moon(*args) -> HtmlElement:
    return svg.Svg(_BASE, *args, svg.Path({"d": "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"}))


def ellipsis(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Circle({"cx": "12", "cy": "12", "r": "1"}),
        svg.Circle({"cx": "19", "cy": "12", "r": "1"}),
        svg.Circle({"cx": "5", "cy": "12", "r": "1"}),
    )


def switch_camera(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M11 19H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"}),
        svg.Path({"d": "M13 5h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-5"}),
        svg.Circle({"cx": "12", "cy": "12", "r": "3"}),
        svg.Path({"d": "m18 22-3-3 3-3"}),
        svg.Path({"d": "m6 2 3 3-3 3"}),
    )


def volume(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Polygon({"points": "11 5 6 9 2 9 2 15 6 15 11 19 11 5"}),
        svg.Path({"d": "M15.54 8.46a5 5 0 0 1 0 7.07"}),
        svg.Path({"d": "M19.07 4.93a10 10 0 0 1 0 14.14"}),
    )


def volume_x(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Polygon({"points": "11 5 6 9 2 9 2 15 6 15 11 19 11 5"}),
        svg.Line({"x1": "22", "x2": "16", "y1": "9", "y2": "15"}),
        svg.Line({"x1": "16", "x2": "22", "y1": "9", "y2": "15"}),
    )


def share(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Circle({"cx": "18", "cy": "5", "r": "3"}),
        svg.Circle({"cx": "6", "cy": "12", "r": "3"}),
        svg.Circle({"cx": "18", "cy": "19", "r": "3"}),
        svg.Line({"x1": "8.59", "x2": "15.42", "y1": "13.51", "y2": "17.49"}),
        svg.Line({"x1": "15.41", "x2": "8.59", "y1": "6.51", "y2": "10.49"}),
    )


def info(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Circle({"cx": "12", "cy": "12", "r": "10"}),
        svg.Path({"d": "M12 16v-4"}),
        svg.Path({"d": "M12 8h.01"}),
    )


def home(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"}),
        svg.Path(
            {
                "d": "M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999"
                "A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"
            }
        ),
    )


def log_out(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"}),
        svg.Polyline({"points": "16 17 21 12 16 7"}),
        svg.Line({"x1": "21", "x2": "9", "y1": "12", "y2": "12"}),
    )


def bell(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"}),
        svg.Path({"d": "M10.3 21a1.94 1.94 0 0 0 3.4 0"}),
    )


def rotate_cw(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"}),
        svg.Path({"d": "M21 3v5h-5"}),
    )


def maximize(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M15 3h6v6"}),
        svg.Path({"d": "M9 21H3v-6"}),
        svg.Path({"d": "M21 3l-7 7"}),
        svg.Path({"d": "M3 21l7-7"}),
    )


def minimize(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M4 14h6v6"}),
        svg.Path({"d": "M20 10h-6V4"}),
        svg.Path({"d": "M14 10l7-7"}),
        svg.Path({"d": "M3 21l7-7"}),
    )


def smartphone(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Rect({"x": "7", "y": "2", "width": "10", "height": "20", "rx": "2"}),
        svg.Path({"d": "M12 18h.01"}),
    )


def wifi(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M5 13a10 10 0 0 1 14 0"}),
        svg.Path({"d": "M8.5 16.5a5 5 0 0 1 7 0"}),
        svg.Path({"d": "M2 8.82a15 15 0 0 1 20 0"}),
        svg.Line({"x1": "12", "y1": "20", "x2": "12.01", "y2": "20"}),
    )


def circle_check(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M21.8 10A10 10 0 1 1 17 3.34"}),
        svg.Path({"d": "m9 11 3 3L22 4"}),
    )


def move(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M5 9l-3 3 3 3"}),
        svg.Path({"d": "M9 5l3-3 3 3"}),
        svg.Path({"d": "M15 19l-3 3-3-3"}),
        svg.Path({"d": "M19 9l3 3-3 3"}),
        svg.Line({"x1": "2", "y1": "12", "x2": "22", "y2": "12"}),
        svg.Line({"x1": "12", "y1": "2", "x2": "12", "y2": "22"}),
    )


def activity(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M22 12h-4l-3 9L9 3l-3 9H2"}),
    )


def mic(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3"}),
        svg.Path({"d": "M19 10v2a7 7 0 0 1-14 0v-2"}),
        svg.Path({"d": "M12 19v3"}),
    )


def x(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M18 6 6 18"}),
        svg.Path({"d": "m6 6 12 12"}),
    )


def video(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "m22 8-6 4 6 4V8Z"}),
        svg.Rect({"x": "2", "y": "6", "width": "14", "height": "12", "rx": "2"}),
    )


def eye(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"}),
        svg.Circle({"cx": "12", "cy": "12", "r": "3"}),
    )


def sun(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Circle({"cx": "12", "cy": "12", "r": "4"}),
        svg.Path({"d": "M12 2v2"}),
        svg.Path({"d": "M12 20v2"}),
        svg.Path({"d": "m4.93 4.93 1.41 1.41"}),
        svg.Path({"d": "m17.66 17.66 1.41 1.41"}),
        svg.Path({"d": "M2 12h2"}),
        svg.Path({"d": "M20 12h2"}),
        svg.Path({"d": "m6.34 17.66-1.41 1.41"}),
        svg.Path({"d": "m19.07 4.93-1.41 1.41"}),
    )


def contrast(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Circle({"cx": "12", "cy": "12", "r": "10"}),
        svg.Path({"d": "M12 18a6 6 0 0 0 0-12v12z"}),
    )


def lock(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Rect({"width": "18", "height": "11", "x": "3", "y": "11", "rx": "2", "ry": "2"}),
        svg.Path({"d": "M7 11V7a5 5 0 0 1 10 0v4"}),
    )


def chevron_left(*args) -> HtmlElement:
    return svg.Svg(_BASE, *args, svg.Path({"d": "m15 18-6-6 6-6"}))


def users(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"}),
        svg.Circle({"cx": "9", "cy": "7", "r": "4"}),
        svg.Path({"d": "M22 21v-2a4 4 0 0 0-3-3.87"}),
        svg.Path({"d": "M16 3.13a4 4 0 0 1 0 7.75"}),
    )


def user_plus(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"}),
        svg.Circle({"cx": "9", "cy": "7", "r": "4"}),
        svg.Path({"d": "M19 8v6"}),
        svg.Path({"d": "M22 11h-6"}),
    )


def sliders(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Path({"d": "M20 7h-9"}),
        svg.Path({"d": "M14 17H5"}),
        svg.Circle({"cx": "17", "cy": "17", "r": "3"}),
        svg.Circle({"cx": "7", "cy": "7", "r": "3"}),
    )


def copy(*args) -> HtmlElement:
    return svg.Svg(
        _BASE,
        *args,
        svg.Rect({"width": "14", "height": "14", "x": "8", "y": "8", "rx": "2", "ry": "2"}),
        svg.Path({"d": "M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"}),
    )
