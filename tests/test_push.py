import asyncio
import os
import re
import stat
from unittest.mock import MagicMock

import pytest
from stario import App
from stario.testing import TestClient

from app.config import Config
from app.features.cam.urls import CAM_APPROVE, CAM_LIVE, CAM_NAME
from app.features.home.urls import NEW_CAM
from app.features.watch.urls import WATCH_LIVE, WATCH_ROOM
from app.main import bootstrap
from app.push.handlers import Push
from app.push.urls import CAM_EVENTS, PUSH_SUB
from app.rooms import Rooms

FCM = "https://fcm.googleapis.com/fcm/send/abc"
APPLE = "https://push.apple.com/xyz"
TAB = {"datastar": '{"tab": "t1"}'}
CAM_TAB = {"datastar": '{"tab": "c1"}'}
CAM_TAB2 = {"datastar": '{"tab": "c2"}'}


class FakeSender:
    calls = []
    status = 201

    def __init__(self, *a, **kw):
        pass

    def send(self, sub, payload):
        FakeSender.calls.append((sub, payload))
        return FakeSender.status


@pytest.fixture
async def pclient(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OFFLINE_PUSH_AFTER", "0.1")
    monkeypatch.delenv("TURN_URLS", raising=False)
    monkeypatch.delenv("COTURN_STATIC_AUTH_SECRET", raising=False)
    monkeypatch.setattr("app.main.PushSender", FakeSender)
    FakeSender.calls = []
    FakeSender.status = 201
    async with TestClient(bootstrap, request_timeout=5) as c:
        yield c


def sub(endpoint=FCM, kinds=("crying", "offline")):
    return {
        "subscription": {"endpoint": endpoint, "keys": {"p256dh": "a" * 43, "auth": "b" * 22}},
        "kinds": list(kinds),
    }


async def room(c) -> str:
    r = await c.post(NEW_CAM.href())
    m = re.search(r"/cam/(\d{6})", r.text)
    assert m
    return m.group(1)


async def approved(c, code) -> str:
    """Register a device, approve it as the cam, return its id."""
    await c.get(WATCH_ROOM.href(code))
    did = c.cookies["device"].partition(".")[0]
    async with c.stream("GET", WATCH_LIVE.href(code), params=TAB, timeout=2) as watch:
        events = watch.iter_events()
        await anext(events)
        for _ in range(50):
            r = await c.post(CAM_APPROVE.href(code, did))
            if r.status_code == 204:
                return did
            await asyncio.sleep(0.1)
        raise AssertionError("approve never succeeded")
    return did


async def test_subscribe_needs_an_approved_device(pclient):
    code = await room(pclient)
    assert (await pclient.post(PUSH_SUB.href(code), json=sub())).status_code == 403


async def test_bad_endpoints_400(pclient):
    code = await room(pclient)
    await approved(pclient, code)
    for bad in ("https://evil.example/x", "http://fcm.googleapis.com/x"):
        assert (await pclient.post(PUSH_SUB.href(code), json=sub(bad))).status_code == 400


async def test_subscribe_and_event_sends(pclient):
    code = await room(pclient)
    await approved(pclient, code)
    for ep in (FCM, APPLE):
        assert (await pclient.post(PUSH_SUB.href(code), json=sub(ep))).status_code == 204
    # the cam cookie is already on the client from NEW_CAM
    assert (
        await pclient.post(CAM_EVENTS.href(code), json={"kind": "crying", "at": 1730000000000})
    ).status_code == 204
    await asyncio.sleep(0.2)
    assert len(FakeSender.calls) == 2
    assert {call[0]["endpoint"] for call in FakeSender.calls} == {FCM, APPLE}
    # non-matching kinds get nothing
    FakeSender.calls = []
    assert (
        await pclient.post(CAM_EVENTS.href(code), json={"kind": "lights_on", "at": 1730000000000})
    ).status_code == 204
    await asyncio.sleep(0.2)
    assert FakeSender.calls == []


async def test_cooldown_blocks_a_second_crying(pclient):
    code = await room(pclient)
    await approved(pclient, code)
    await pclient.post(PUSH_SUB.href(code), json=sub())
    for at in (1, 2):
        await pclient.post(CAM_EVENTS.href(code), json={"kind": "crying", "at": at})
    await asyncio.sleep(0.2)
    assert len(FakeSender.calls) == 1


async def test_410_deletes_the_sub(pclient):
    code = await room(pclient)
    await approved(pclient, code)
    await pclient.post(PUSH_SUB.href(code), json=sub())
    FakeSender.status = 410
    await pclient.post(CAM_EVENTS.href(code), json={"kind": "crying", "at": 1})
    await asyncio.sleep(0.2)
    FakeSender.status = 201
    FakeSender.calls = []
    await pclient.post(CAM_EVENTS.href(code), json={"kind": "crying", "at": 2 + 130000})
    # cooldown passes (kind at +130s wall? cooldown uses monotonic: post a new kind)
    await pclient.post(CAM_EVENTS.href(code), json={"kind": "loud", "at": 3})
    await asyncio.sleep(0.2)
    assert all(call[0]["endpoint"] != FCM for call in FakeSender.calls)


async def test_cam_offline_after_the_delay(pclient):
    code = await room(pclient)
    await approved(pclient, code)
    await pclient.post(PUSH_SUB.href(code), json=sub())
    async with pclient.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2):
        pass
    await asyncio.sleep(0.5)
    assert any(call[1].get("kind") == "offline" for call in FakeSender.calls)


async def test_cam_reconnect_cancels_offline(pclient):
    code = await room(pclient)
    await approved(pclient, code)
    await pclient.post(PUSH_SUB.href(code), json=sub())
    async with pclient.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2):
        pass
    async with pclient.stream("GET", CAM_LIVE.href(code), params=CAM_TAB2, timeout=2):
        await asyncio.sleep(0.3)
    assert not any(call[1].get("kind") == "offline" for call in FakeSender.calls)


async def test_remove_viewer_drops_subs(pclient):
    code = await room(pclient)
    did = await approved(pclient, code)
    await pclient.post(PUSH_SUB.href(code), json=sub())
    from app.features.cam.urls import CAM_REMOVE

    assert (await pclient.post(CAM_REMOVE.href(code, did))).status_code == 204
    FakeSender.calls = []
    await pclient.post(CAM_EVENTS.href(code), json={"kind": "crying", "at": 1})
    await asyncio.sleep(0.2)
    assert FakeSender.calls == []


async def test_vapid_key_created_and_reused(tmp_path):
    from app.push.vapid import load

    p = tmp_path / "vapid.pem"
    path1, pub1 = load(p)
    assert p.exists()
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    path2, pub2 = load(p)
    assert (path1, pub1) == (path2, pub2)


async def test_push_title_uses_the_camera_name(pclient):
    code = await room(pclient)
    await approved(pclient, code)
    assert (await pclient.post(CAM_NAME.href(code), json={"name": "Nursery"})).status_code == 204
    await pclient.post(PUSH_SUB.href(code), json=sub())
    await pclient.post(CAM_EVENTS.href(code), json={"kind": "crying", "at": 1})
    await asyncio.sleep(0.2)
    assert FakeSender.calls[0][1]["title"] == "Nursery"


async def test_shutdown_ends_the_offline_timer_without_a_push(tmp_path):
    # A deploy drops every camera; that is not an offline camera.
    config = Config(
        "Philomena", tmp_path, (), (), "", 0, "http://localhost", offline_push_after=3600
    )
    sender = MagicMock()
    push = Push(rooms=Rooms(), db=MagicMock(), sender=sender, config=config)
    app = App()
    push.cam_gone("123456", app)
    task = push.rooms.offline_tasks["123456"]
    await asyncio.sleep(0)
    app.signal_shutdown()
    await asyncio.wait_for(task, 1)
    sender.send.assert_not_called()
