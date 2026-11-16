"""In-memory room registry: one camera tab and a set of viewer tabs per code."""

import asyncio
import re
import secrets
from dataclasses import dataclass, field

from stario.datastar.format import string_literal
from stario.json import dumps as json_dumps

CODE_LENGTH = 6
_LINK_RE = re.compile(r"/(?:watch|cam)/(\d{6})(?!\d)")


def valid_code(code: str) -> bool:
    return len(code) == CODE_LENGTH and code.isdecimal()


def parse_code(text: str) -> str:
    """The code in what a person pasted: a watch link, "482 913", or "482-913"."""
    if link := _LINK_RE.search(text):
        return link[1]
    return "".join(ch for ch in text if ch.isdecimal())


def receive_script(msg: dict) -> str:
    """A `sse.execute_script` payload that hands `msg` to `app.rtc.receive`."""
    return "app.rtc.receive(" + string_literal(json_dumps(msg)) + ")"


@dataclass(slots=True)
class Room:
    cam: str | None = None
    viewers: dict[str, str] = field(default_factory=dict)  # tab -> device_id


@dataclass(slots=True)
class Rooms:
    by_code: dict[str, Room] = field(default_factory=dict)
    offline_tasks: dict[str, asyncio.Task[None]] = field(default_factory=dict)

    def random_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):0{CODE_LENGTH}d}"

    def room(self, code: str) -> Room | None:
        return self.by_code.get(code)

    def cam_join(self, code: str, tab: str) -> str | None:
        room = self.by_code.setdefault(code, Room())
        room.viewers.pop(tab, None)
        old = room.cam
        room.cam = tab
        return old if old is not None and old != tab else None

    def viewer_join(self, code: str, tab: str, device_id: str) -> None:
        room = self.by_code.setdefault(code, Room())
        if tab != room.cam:
            room.viewers[tab] = device_id

    def devices_online(self, code: str) -> set[str]:
        room = self.by_code.get(code)
        return set(room.viewers.values()) if room is not None else set()

    def device_tabs(self, code: str, device_id: str) -> list[str]:
        room = self.by_code.get(code)
        if room is None:
            return []
        return [t for t, d in room.viewers.items() if d == device_id]

    def leave(self, code: str, tab: str) -> None:
        room = self.by_code.get(code)
        if room is None:
            return
        if room.cam == tab:
            room.cam = None
        room.viewers.pop(tab, None)
        if room.cam is None and not room.viewers:
            del self.by_code[code]

    def cam_of(self, code: str) -> str | None:
        room = self.by_code.get(code)
        return room.cam if room is not None else None

    def viewers_of(self, code: str) -> list[str]:
        room = self.by_code.get(code)
        return list(room.viewers) if room is not None else []

    def can_signal(self, code: str, sender: str, to: str) -> bool:
        room = self.by_code.get(code)
        if room is None or sender == to:
            return False
        if sender == room.cam:
            return to in room.viewers
        return sender in room.viewers and to == room.cam
