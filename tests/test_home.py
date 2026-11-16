import re

from app.features.cam.urls import CAM, CAM_LIVE
from app.features.home.urls import HOME, NEW_CAM, WATCH
from app.features.watch.urls import WATCH_ROOM


async def room_code(client) -> str:
    r = await client.post(NEW_CAM.href())
    match = re.search(r"/cam/(\d{6})", r.text)
    assert match
    return match.group(1)


async def test_home_loads(client):
    r = await client.get(HOME.href())
    assert r.status_code == 200
    assert 'id="home"' in r.text
    assert "css/output" in r.text
    assert "manifest.webmanifest" in r.text


async def test_new_cam_navigates_to_a_room(client):
    r = await client.post(NEW_CAM.href(), json={"tab": "t1"})
    assert r.status_code == 200
    assert "window.location" in r.text
    assert re.search(r"/cam/\d{6}", r.text)
    assert re.fullmatch(r"\d{6}\..+", client.cookies.get("cam", ""))


async def test_watch_with_a_bad_code_fails(client):
    r = await client.get(WATCH.href(), params={"code": "abc"})
    assert r.status_code == 400
    assert "6 digits" in r.text


async def test_watch_with_a_good_code_redirects(client):
    r = await client.get(WATCH.href(), params={"code": "123456"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location") == WATCH_ROOM.href("123456")


async def test_watch_reads_a_pasted_link_or_spaced_code(client):
    for pasted in (
        "https://monitor.example.com/watch/482913",
        "http://localhost:8000/watch/482913?x=1",
        "482 913",
        " 482-913\n",
    ):
        r = await client.get(WATCH.href(), params={"code": pasted}, follow_redirects=False)
        assert r.status_code == 303, pasted
        assert r.headers.get("location") == WATCH_ROOM.href("482913"), pasted


async def test_home_shows_why_philomena(client):
    r = await client.get(HOME.href())
    assert "Why Philomena" in r.text
    assert "dad of three" in r.text


async def test_pages_carry_link_previews(client):
    code = await room_code(client)
    for url in (
        HOME.href(),
        CAM.href(code),
        WATCH_ROOM.href(code),
        WATCH_ROOM.href("654321"),  # the 404 page too
    ):
        r = await client.get(url)
        assert 'property="og:title"' in r.text, url
        m = re.search(r'property="og:image" content="([^"]+)"', r.text)
        assert m, url
        assert m.group(1).startswith("http://localhost:8000/static/og"), m.group(1)
        assert 'name="twitter:card" content="summary_large_image"' in r.text


async def test_watch_unknown_code_is_404(client):
    r = await client.get(WATCH_ROOM.href("654321"))
    assert r.status_code == 404
    assert "No camera has this code" in r.text


async def test_watch_page_renders_for_a_known_code(client):
    code = await room_code(client)
    r = await client.get(WATCH_ROOM.href(code))
    assert r.status_code == 200
    assert 'id="watch"' in r.text
    assert "Waiting for the camera" in r.text
    assert client.cookies.get("device")


async def test_cam_page_loads(client):
    code = await room_code(client)
    r = await client.get(CAM.href(code))
    assert r.status_code == 200
    assert 'id="cam"' in r.text
    assert f"/cam/{code}/live" in r.text
    assert code in r.text


async def test_cam_page_is_owner_only(client):
    code = await room_code(client)
    # a phone with a well-formed but wrong cam cookie is not the owner
    r = await client.get(CAM.href(code), cookies={"cam": "000000.deadbeef"})
    assert r.status_code == 403
    assert "belongs to another phone" in r.text
    r = await client.get(
        CAM_LIVE.href(code),
        params={"datastar": '{"tab": "c1"}'},
        cookies={"cam": "000000.deadbeef"},
    )
    assert r.status_code == 403


async def test_cam_page_renders_a_qr_for_the_watch_url(client):
    code = await room_code(client)
    r = await client.get(CAM.href(code), headers={"host": "monitor.example.com"})
    assert r.status_code == 200
    assert "<svg" in r.text
    assert f"https://monitor.example.com/watch/{code}" in r.text


async def test_cam_page_skips_the_qr_on_a_bad_host(client):
    code = await room_code(client)
    r = await client.get(CAM.href(code), headers={"host": "not_a_valid.host"})
    assert r.status_code == 200
    assert "data-url" not in r.text


async def test_cam_code_is_reused_next_night(client):
    code = await room_code(client)
    r = await client.post(NEW_CAM.href())
    assert code in r.text


async def test_pages_404_for_a_bad_code(client):
    assert (await client.get(CAM.href("abc"))).status_code == 400
    assert (await client.get(CAM.href("654321"))).status_code == 404
    assert (await client.get(WATCH_ROOM.href("12345"))).status_code == 400
