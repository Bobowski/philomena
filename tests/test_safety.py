import re

from litewriter import LiteWriter

from app.features.cam.urls import (
    CAM,
    CAM_APPROVE,
    CAM_LIVE,
    CAM_NEW_CODE,
    CAM_REMOVE,
)
from app.features.home.urls import NEW_CAM
from app.features.watch.urls import WATCH_LIVE, WATCH_ROOM
from app.rooms import data as rooms_data

CAM_TAB = {"datastar": '{"tab": "c1"}'}
VIEW_TAB = {"datastar": '{"tab": "v1"}'}


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


async def until_text(events, text: str) -> str:
    async for e in events:
        if text in e["data"]:
            return e["data"]
    raise AssertionError(f"stream ended before {text}")


def device_id(client) -> str:
    return client.cookies["device"].partition(".")[0]


async def test_pending_knock_repaints_the_cam_panel(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2) as cam:
        cam_events = cam.iter_events()
        await anext(cam_events)
        async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=2):
            card = await until_text(cam_events, "wants to watch")
            assert "Allow" in card
            await until_type(cam_events, "knock")


async def test_approve_and_remove_permissions(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    did = device_id(client)
    bad_cam = {"cam": "000000.deadbeef"}
    # a phone that is not the camera cannot approve or remove
    assert (await client.post(CAM_APPROVE.href(code, did), cookies=bad_cam)).status_code == 403
    assert (await client.post(CAM_REMOVE.href(code, did), cookies=bad_cam)).status_code == 403
    # an unknown device is a 404
    assert (await client.post(CAM_APPROVE.href(code, "zz99"))).status_code == 404


async def test_remove_kicks_and_ends_the_viewer(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    did = device_id(client)
    async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=2) as cam:
        cam_events = cam.iter_events()
        await anext(cam_events)
        async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=2) as watch:
            watch_events = watch.iter_events()
            await until_type(watch_events, "pending")
            r = await client.post(CAM_APPROVE.href(code, did))
            assert r.status_code == 204
            await until_type(watch_events, "cam")
            await until_type(cam_events, "join")
            r = await client.post(CAM_REMOVE.href(code, did))
            assert r.status_code == 204
            kick = await until_type(cam_events, "kick")
            assert '"from":"v1"' in kick
            await until_type(watch_events, "removed")


async def test_approved_device_joins_without_pending(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    did = device_id(client)
    async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=2) as watch:
        events = watch.iter_events()
        await until_type(events, "pending")
        await client.post(CAM_APPROVE.href(code, did))
        await until_type(events, "cam")
    # reconnect: no pending, the cam message comes right after ice
    async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=2) as watch:
        events = watch.iter_events()
        await until_type(events, "ice")
        second = await until_type(events, "cam")
        assert '"data":false' in second


async def test_new_code_removes_everyone(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    did = device_id(client)
    async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=2) as watch:
        events = watch.iter_events()
        await until_type(events, "pending")
        await client.post(CAM_APPROVE.href(code, did))
        await until_type(events, "cam")
        r = await client.post(CAM_NEW_CODE.href(code))
        assert r.status_code == 200
        found = re.search(r"/cam/(\d{6})", r.text)
        assert found
        new_code = found.group(1)
        assert new_code != code
        await until_type(events, "removed")
    assert client.cookies["cam"].startswith(new_code)
    assert (await client.get(WATCH_ROOM.href(code))).status_code == 404
    assert (await client.get(WATCH_ROOM.href(new_code))).status_code == 200


async def test_watch_page_renders_remote_controls(client):
    code = await room_code(client)
    r = await client.get(WATCH_ROOM.href(code))
    assert "Switch camera" in r.text
    assert "Sound only" in r.text
    assert "Tonight" in r.text
    assert "data-chart" in r.text
    assert "Alerts" in r.text
    assert "Crying" in r.text
    assert "Stirring" in r.text
    assert "Loud sound" in r.text
    assert "Movement" in r.text
    assert "Lights" in r.text
    assert "data-motion-meter" in r.text
    assert "Talking…" in r.text


async def test_cam_page_renders_the_talk_back_audio(client):
    code = await room_code(client)
    r = await client.get(CAM.href(code))
    assert 'data-rtc="talk"' in r.text


async def test_pending_cap(tmp_path):
    async with LiteWriter(tmp_path / "t.sqlite3", schema=rooms_data.schema) as db:
        for i in range(7):
            await db.write(rooms_data.upsert_pending, "123456", f"d{i}")
        rows = db.query(
            "SELECT device_id FROM approvals WHERE code = '123456' AND status = 'pending'"
        )
        assert [r[0] for r in rows] == ["d2", "d3", "d4", "d5", "d6"]
