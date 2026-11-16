from dataclasses import dataclass

from stario import App, Context, Relay, Writer
from stario.datastar import read_signals

from app.features.room.urls import SIGNAL
from app.rooms import Rooms, valid_code

KINDS = ("offer", "answer", "candidate")


@dataclass(frozen=True, slots=True)
class RoomPage:
    rooms: Rooms
    relay: Relay[dict]

    def register(self, app: App) -> None:
        app.add(SIGNAL, self.signal)

    async def signal(self, c: Context, w: Writer) -> None:
        code = c.match.params["code"]
        if not valid_code(code):
            w.text("code must be 6 digits", status=400)
            return
        signals = await read_signals(c.req)
        tab = str(signals.get("tab", ""))
        to = str(signals.get("to", ""))
        kind = str(signals.get("kind", ""))
        if not (tab.isalnum() and len(tab) <= 32 and to.isalnum() and len(to) <= 32):
            w.text("tab and to must be short ids", status=400)
            return
        if kind not in KINDS:
            w.text("kind must be offer, answer or candidate", status=400)
            return
        if self.rooms.room(code) is None:
            w.text("no such room", status=404)
            return
        if not self.rooms.can_signal(code, tab, to):
            w.text("peers must be in the room on opposite sides", status=403)
            return
        w.empty()
        self.relay.publish(
            f"peer.{to}",
            {"type": kind, "from": tab, "data": signals.get("data")},
        )
