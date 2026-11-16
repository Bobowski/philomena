import re
from pathlib import Path

from app.config import Config
from app.features.cam.urls import CAM_APPROVE, CAM_LIVE
from app.features.home.urls import NEW_CAM
from app.features.room.urls import SIGNAL
from app.features.watch.urls import WATCH_LIVE, WATCH_ROOM
from app.rooms.ice import ice_servers

CODE = "123456"
CAM_TAB = {"datastar": '{"tab": "c1"}'}
CAM_TAB_2 = {"datastar": '{"tab": "c2"}'}
VIEW_TAB = {"datastar": '{"tab": "v1"}'}
VIEW_TAB_2 = {"datastar": '{"tab": "v2"}'}


async def room_code(client) -> str:
    r = await client.post(NEW_CAM.href())
    match = re.search(r"/cam/(\d{6})", r.text)
    assert match
    return match.group(1)


async def until_type(events, kind: str) -> str:
    async for e in events:
        if f'"type":"{kind}"' in e["data"]:
            return e["data"]
    raise AssertionError(f"stream ended before {kind}")


def device_id(client) -> str:
    return client.cookies["device"].partition(".")[0]


async def approve(client, code) -> str:
    """Approve the client's own device; returns the device id."""
    did = device_id(client)
    r = await client.post(CAM_APPROVE.href(code, did))
    assert r.status_code == 204
    return did


async def test_cam_stream_sends_ice_first(client):
    code = await room_code(client)
    async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2) as live:
        events = live.iter_events()
        first = await anext(events)
        assert "app.rtc.receive" in first["data"]
        assert '"type":"ice"' in first["data"]
        assert "stun:stun.l.google.com:19302" in first["data"]
        assert "username" not in first["data"]


async def test_viewer_join_signals_and_disconnect(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2) as cam:
        cam_events = cam.iter_events()
        await anext(cam_events)
        async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=2) as watch:
            watch_events = watch.iter_events()
            assert '"type":"ice"' in (await anext(watch_events))["data"]
            assert '"type":"pending"' in (await anext(watch_events))["data"]
            await approve(client, code)
            cam_state = await until_type(watch_events, "cam")
            assert '"data":true' in cam_state
            join = await until_type(cam_events, "join")
            assert '"from":"v1"' in join

            r = await client.post(
                SIGNAL.href(code),
                json={
                    "tab": "v1",
                    "to": "c1",
                    "kind": "answer",
                    "data": {"sdp": "x"},
                },
            )
            assert r.status_code == 204
            answer = await until_type(cam_events, "answer")
            assert '"from":"v1"' in answer

        # the viewer stream is closed now
        leave = await until_type(cam_events, "leave")
        assert '"from":"v1"' in leave


async def test_cam_gone_tells_the_viewer(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=2) as watch:
        watch_events = watch.iter_events()
        await anext(watch_events)
        await anext(watch_events)  # pending
        await approve(client, code)
        assert '"data":false' in await until_type(watch_events, "cam")
        async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2) as cam:
            cam_events = cam.iter_events()
            await anext(cam_events)
            # the viewer hears the camera arrived, then joins it
            assert '"data":true' in await until_type(watch_events, "cam")
            join = await until_type(cam_events, "join")
            assert '"from":"v1"' in join
        # the camera stream is closed now
        assert '"data":false' in await until_type(watch_events, "cam")


async def test_second_cam_replaces_the_first(client):
    code = await room_code(client)
    async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2) as cam1:
        events1 = cam1.iter_events()
        await anext(events1)
        async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB_2, timeout=2) as cam2:
            events2 = cam2.iter_events()
            assert '"type":"ice"' in (await anext(events2))["data"]
            replaced = await until_type(events1, "replaced")
            assert replaced


async def test_signal_validation(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2) as cam:
        cam_events = cam.iter_events()
        await anext(cam_events)
        async with (
            client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=2) as w1,
            client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB_2, timeout=2) as w2,
        ):
            e1, e2 = w1.iter_events(), w2.iter_events()
            await anext(e1)
            await anext(e2)
            await until_type(e1, "pending")
            await until_type(e2, "pending")
            await approve(client, code)
            await until_type(e1, "cam")
            await until_type(e2, "cam")
            body = {"tab": "v1", "to": "c1", "kind": "answer", "data": {}}
            # a recipient that is not in the room
            r = await client.post(SIGNAL.href(code), json={**body, "to": "ghost"})
            assert r.status_code == 403
            # viewer to viewer is not a side pair
            r = await client.post(SIGNAL.href(code), json={**body, "to": "v2"})
            assert r.status_code == 403
            # an unknown kind
            r = await client.post(SIGNAL.href(code), json={**body, "kind": "bogus"})
            assert r.status_code == 400
            # a room that does not exist
            r = await client.post(SIGNAL.href("999999"), json=body)
            assert r.status_code == 404
            # a malformed code
            r = await client.post(SIGNAL.href("abcdef"), json=body)
            assert r.status_code == 400
            # a healthy cam -> viewer signal
            r = await client.post(
                SIGNAL.href(code),
                json={
                    "tab": "c1",
                    "to": "v1",
                    "kind": "offer",
                    "data": {"sdp": "y"},
                },
            )
            assert r.status_code == 204


def test_turn_entry_carries_every_url_with_transport():
    config = Config(
        app_name="t",
        data_dir=Path("/tmp"),
        stun_urls=("stun:monitor.example.com:3478",),
        turn_urls=(
            "turn:monitor.example.com:3478?transport=udp",
            "turn:monitor.example.com:3478?transport=tcp",
        ),
        turn_secret="s3cret",
        turn_ttl=3600,
        public_url="https://monitor.example.com",
    )
    stun, turn = ice_servers(config)
    assert stun["urls"] == ["stun:monitor.example.com:3478"]
    assert turn["urls"] == [
        "turn:monitor.example.com:3478?transport=udp",
        "turn:monitor.example.com:3478?transport=tcp",
    ]
    assert re.fullmatch(r"\d+:[0-9a-f]+", str(turn["username"]))
    assert turn["credential"]


async def test_ice_includes_turn_when_configured(turn_client):
    code = await room_code(turn_client)
    async with turn_client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2) as live:
        events = live.iter_events()
        data = (await anext(events))["data"]
        assert "turn:turn.example.com:3478" in data
        match = re.search(r'"username":"(\d+):[0-9a-f]+"', data)
        assert match, data
        assert '"credential":"' in data
