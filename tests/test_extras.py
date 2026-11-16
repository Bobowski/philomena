import asyncio
import re

from app.features.cam.urls import CAM_LIVE, CAM_NAME
from app.features.home.urls import HOME, NEW_CAM
from app.features.watch.urls import WATCH_LIVE, WATCH_ROOM

CAM_TAB = {"datastar": '{"tab": "c1"}'}
VIEW_TAB = {"datastar": '{"tab": "v1"}'}


async def room_code(client) -> str:
    r = await client.post(NEW_CAM.href())
    m = re.search(r"/cam/(\d{6})", r.text)
    assert m
    return m.group(1)


async def test_name_needs_the_cam_cookie(client):
    code = await room_code(client)
    r = await client.post(CAM_NAME.href(code), json={"name": "Nursery"}, cookies={"cam": "bad"})
    assert r.status_code == 403


async def test_name_too_long(client):
    code = await room_code(client)
    r = await client.post(CAM_NAME.href(code), json={"name": "x" * 31})
    assert r.status_code == 400


async def test_name_reaches_the_viewer_stream(client):
    code = await room_code(client)
    await client.get(WATCH_ROOM.href(code))
    did = client.cookies["device"].partition(".")[0]
    from app.features.cam.urls import CAM_APPROVE

    async with client.stream("GET", CAM_LIVE.href(code), params=CAM_TAB, timeout=5) as cam:
        cam_events = cam.iter_events()
        await anext(cam_events)
        async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=5) as watch:
            events = watch.iter_events()
            await anext(events)
            r = await client.post(CAM_APPROVE.href(code, did))
            for _ in range(50):
                if r.status_code == 204:
                    break
                await asyncio.sleep(0.1)
                r = await client.post(CAM_APPROVE.href(code, did))
            assert r.status_code == 204
            r = await client.post(CAM_NAME.href(code), json={"name": "Nursery"})
            assert r.status_code == 204
            async for e in events:
                if "Nursery" in e["data"]:
                    return
            raise AssertionError("name never reached the viewer")


async def test_home_lists_only_approved_cameras(client):
    code = await room_code(client)
    # no approved device yet: the section is absent
    r = await client.get(HOME.href())
    assert "Your cameras" not in r.text
    # visit the watch page to get a device cookie, knock, get approved
    await client.get(WATCH_ROOM.href(code))
    did = client.cookies["device"].partition(".")[0]
    from app.features.cam.urls import CAM_APPROVE

    async with client.stream("GET", WATCH_LIVE.href(code), params=VIEW_TAB, timeout=3) as watch:
        events = watch.iter_events()
        await anext(events)
        r = await client.post(CAM_APPROVE.href(code, did))
        for _ in range(50):
            if r.status_code == 204:
                break
            await asyncio.sleep(0.1)
            r = await client.post(CAM_APPROVE.href(code, did))
        assert r.status_code == 204
    r = await client.get(HOME.href())
    assert "Your cameras" in r.text
    assert "Camera 123 456" in r.text or code[:3] in r.text
    # a room this device has not joined does not show
    r2 = await client.post(NEW_CAM.href(), cookies={"cam": "000000.deadbeef"})
    m2 = re.search(r"/cam/(\d{6})", r2.text)
    assert m2 and m2.group(1) != code
    await client.get(WATCH_ROOM.href(m2.group(1)))
    r = await client.get(HOME.href())
    assert f"/watch/{m2.group(1)}" not in r.text
