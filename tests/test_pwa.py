from app.features.pwa.urls import HEALTH, MANIFEST, SW_JS


async def test_manifest_is_served(client):
    r = await client.get(MANIFEST.href())
    assert r.status_code == 200
    assert r.headers.get("content-type").startswith("application/manifest+json")
    assert '"name":"Philomena"' in r.text
    assert '"purpose":"maskable"' in r.text


async def test_sw_js_is_served_from_the_root(client):
    r = await client.get(SW_JS.href())
    assert r.status_code == 200
    assert r.headers.get("content-type").startswith("text/javascript")
    assert "skipWaiting" in r.text
    assert "clients.claim" in r.text


async def test_health(client):
    r = await client.get(HEALTH.href())
    assert r.status_code == 200
    assert r.text == "ok"
