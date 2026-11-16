"""End-to-end check of the connection flow in a real browser.

Run:  uv run --with playwright python scripts/e2e.py
Once: uv run --with playwright playwright install chromium

Starts the app on a free localhost port, pairs a fake camera with a fake
viewer over WebRTC, and saves screenshots to /tmp/philomena-shots/.
Not part of `just check`.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
SHOTS = Path("/tmp/philomena-shots")
# the open sheet shows all of its content: no scroll inside the box
NO_SCROLL = (
    "() => [...document.querySelectorAll('dialog[open] .sheet-box')]"
    ".every(b => b.scrollHeight <= b.clientHeight + 1)"
)


def write_still(path: str) -> None:
    """A 320x240 y4m: a gray frame with a darker block, 30 identical frames."""
    w, h = 320, 240
    header = f"YUV4MPEG2 W{w} H{h} F30:1 Ip A1:1 C420jpeg\n".encode()
    y = bytearray([128] * (w * h))
    for yy in range(40, 120):
        for xx in range(60, 160):
            y[yy * w + xx] = 60
    uv = bytes([128] * (w // 2 * h // 2))
    Path(path).write_bytes(header + (b"FRAME\n" + bytes(y) + uv + uv) * 30)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def main() -> None:
    # a stale stylesheet would let layout bugs pass — rebuild it first
    subprocess.run(["just", "css"], cwd=ROOT, check=True)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    SHOTS.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "STARIO_HOST": "127.0.0.1",
        "STARIO_PORT": str(port),
        "PROJECT_DATA_DIR": tempfile.mkdtemp(prefix="philomena-e2e-"),
        "TURN_URLS": "",
        "COTURN_STATIC_AUTH_SECRET": "",
        "OFFLINE_PUSH_AFTER": "0.1",
    }
    server = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"{base}/health", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("app did not start")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=[
                    "--use-fake-device-for-media-stream",
                    "--use-fake-ui-for-media-stream",
                    "--disable-dev-shm-usage",
                ]
            )
            cam_ctx = await browser.new_context(
                viewport={"width": 390, "height": 844},
                permissions=["camera", "microphone"],
                color_scheme="dark",
            )
            cam = await cam_ctx.new_page()
            await cam.goto(base)
            # a dark phone setting gives the night look before the first paint
            assert await cam.evaluate("document.documentElement.dataset.theme") == "night"
            await cam.screenshot(path=str(SHOTS / "home.png"))
            await cam.get_by_role("button", name="Comes with me").click()
            await cam.wait_for_timeout(600)
            await cam.screenshot(path=str(SHOTS / "home-code-form.png"))
            await cam.screenshot(path=str(SHOTS / "home-full.png"), full_page=True)
            await cam.get_by_role("button", name="Stays with the baby").click()
            await cam.wait_for_url("**/cam/*")
            code = cam.url.rsplit("/", 1)[-1]
            print("camera code:", code)
            await cam.wait_for_timeout(1200)
            await cam.screenshot(path=str(SHOTS / "cam-waiting.png"))
            # the invite sheet opens on its own and fits without a scroll
            await cam.get_by_role("button", name="Copy link").wait_for(timeout=5000)
            assert await cam.evaluate(NO_SCROLL), "invite sheet scrolls"
            # the whole QR fits its white box: the SVG scales, it is not cut
            assert await cam.evaluate(
                "() => { const b = document.querySelector('[data-url]');"
                " const s = b.querySelector('svg').getBoundingClientRect();"
                " const r = b.getBoundingClientRect();"
                " return s.width > 100 && s.right <= r.right && s.bottom <= r.bottom; }"
            ), "QR is cut"
            await cam.screenshot(path=str(SHOTS / "cam-invite.png"))
            await cam.keyboard.press("Escape")
            await cam.get_by_role("button", name="Settings").click()
            await cam.wait_for_timeout(400)
            assert await cam.evaluate(NO_SCROLL), "settings sheet scrolls"
            await cam.screenshot(path=str(SHOTS / "cam-settings.png"))
            await cam.keyboard.press("Escape")
            await cam.get_by_role("button", name="Viewers").click()
            await cam.wait_for_timeout(400)
            await cam.screenshot(path=str(SHOTS / "cam-viewers-empty.png"))
            await cam.keyboard.press("Escape")
            # back asks first: a tap must not stop the camera
            await cam.get_by_role("button", name="Back to start").click()
            await cam.get_by_role("button", name="Keep on").first.wait_for(timeout=2000)
            await cam.screenshot(path=str(SHOTS / "cam-leave.png"))
            await cam.get_by_role("button", name="Keep on").first.click()

            watch_ctx = await browser.new_context(
                viewport={"width": 390, "height": 844},
                has_touch=True,
                permissions=["camera", "microphone", "notifications"],
                color_scheme="dark",
            )
            watch = await watch_ctx.new_page()
            await watch.goto(f"{base}/watch/{code}")
            await watch.wait_for_timeout(1500)
            assert "approve this phone" in await watch.inner_text("body")
            await watch.screenshot(path=str(SHOTS / "watch-pending.png"))
            # the knock card appears on the camera phone; approve it
            await cam.get_by_role("button", name="Allow").wait_for(timeout=10000)
            await cam.wait_for_timeout(300)
            await cam.screenshot(path=str(SHOTS / "cam-allow-card.png"))
            await cam.get_by_role("button", name="Allow").click()
            # a stranger gets the owner-only page
            stranger_ctx = await browser.new_context(viewport={"width": 390, "height": 844})
            stranger = await stranger_ctx.new_page()
            await stranger.goto(f"{base}/cam/{code}")
            assert "belongs to another phone" in await stranger.inner_text("body")
            await stranger.close()
            await watch.wait_for_function(
                "() => { const v = document.querySelector('[data-rtc=remote]');"
                " return v && v.videoWidth > 0; }",
                timeout=20000,
            )
            print("watch: video frames flowing")
            await watch.wait_for_timeout(800)
            await cam.screenshot(path=str(SHOTS / "cam-live.png"))
            # the viewer opens on the glance view: the word, the meters, the strip
            assert await watch.evaluate("document.querySelector('#watch').dataset.mode") == "glance"
            word = await watch.locator("[data-glance-word]").inner_text()
            # the fake feed moves and beeps, so the camera may already report stirring
            assert word in ("Calm", "Stirring"), repr(word)
            await watch.screenshot(path=str(SHOTS / "watch-live-muted.png"))
            await watch.get_by_role("button", name="Turn on sound").click()
            # the fake device beeps: the meter must light up
            await watch.wait_for_function(
                "() => parseFloat("
                "document.querySelector('[data-meter]').style.getPropertyValue('--level')"
                " || '0') > 0",
                timeout=3000,
            )
            print("meter is live")
            await watch.screenshot(path=str(SHOTS / "watch-live-meter.png"))
            # a small phone (iPhone SE): the glance view fits without a scroll
            await watch.set_viewport_size({"width": 375, "height": 667})
            await watch.wait_for_timeout(300)
            fits = await watch.evaluate(
                "() => { const m = document.querySelector('#watch');"
                " const w = document.querySelector('[data-glance-word]').getBoundingClientRect();"
                " const d = document.querySelector('[data-part=dock]').getBoundingClientRect();"
                " return m.scrollHeight <= m.clientHeight + 1 && w.height > 40"
                " && d.bottom <= innerHeight + 1; }"
            )
            assert fits, "glance view does not fit a small phone"
            await watch.screenshot(path=str(SHOTS / "watch-small.png"))
            await watch.set_viewport_size({"width": 390, "height": 844})

            # adaptive: the animated fake video reports "active" at 24 fps
            out_fps = (
                "async () => { let f = 0;"
                " for (const p of Object.values(app.rtc.pcs)) {"
                "  const s = await p.pc.getStats();"
                "  s.forEach(r => {"
                "   if (r.type === 'outbound-rtp' && r.kind === 'video')"
                "    f = r.framesPerSecond ?? f;"
                "  });"
                " }"
                " return f; }"
            )
            await cam.wait_for_function("() => app.rtc._fps === 24", timeout=5000)
            await cam.wait_for_timeout(1500)
            fps = await cam.evaluate(out_fps)
            assert fps >= 15, fps
            print("active cam fps:", fps)
            # the movement meter fills from the camera's frame diff
            await watch.wait_for_function(
                "() => parseFloat(document.querySelector('[data-motion-meter]')"
                ".style.getPropertyValue('--level') || '0') > 0",
                timeout=5000,
            )
            await watch.screenshot(path=str(SHOTS / "watch-moving.png"))
            # every bar control must fit the 390px viewport
            for name in ("Sound", "Talk", "Picture", "Screen off", "More"):
                box = await watch.get_by_role("button", name=name, exact=True).bounding_box()
                assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390, (name, box)
            # camera events drive the alerts now; pause the live sampler so the
            # fed samples alone drive the state machine
            await cam.evaluate(
                "app.rtc.detect.live = false; app.rtc.detect.reset(); app.rtc.detect.floorDb = -60"
            )
            await watch.get_by_role("button", name="Screen off").click()
            ov = await watch.locator(".lights-out").bounding_box()
            assert ov and ov["width"] >= 390 and ov["height"] >= 800, ov
            await watch.screenshot(path=str(SHOTS / "watch-dim.png"))
            # 4 s of cry-shaped samples → a crying event reaches the viewer
            await cam.evaluate(
                "(() => { const T = performance.now(); for (let i = 0; i < 40; i++)"
                " app.rtc.detect.feed({level: -45, f0: 400, clarity: 0.8, band: 0.8,"
                "  motion: false, luma: 100, t: T + i * 100}); })()"
            )
            await watch.wait_for_function(
                "() => document.querySelector('[data-event-banner]')?.innerText.includes('Crying')",
                timeout=5000,
            )
            await watch.wait_for_function(
                "() => document.querySelector('#watch').dataset.alerted === '1'",
                timeout=5000,
            )
            await watch.wait_for_function(
                "() => document.querySelector('[data-glance-word]').textContent === 'Crying'",
                timeout=5000,
            )
            print("crying event alerted; the glance word says Crying")
            await watch.screenshot(path=str(SHOTS / "watch-alert-crying.png"))
            # rotate once through the More sheet: the video box gets 90deg
            await watch.get_by_role("button", name="More").click()
            await watch.get_by_role("button", name="Rotate").click()
            await watch.keyboard.press("Escape")
            tf = await watch.eval_on_selector("[data-view]", "el => el.style.transform")
            assert "90deg" in tf, tf
            print("rotated:", tf)
            await watch.screenshot(path=str(SHOTS / "watch-rotated.png"))

            async def settle(page):
                # sheets animate ~300 ms; wait until their geometry stops
                last = None
                for _ in range(20):
                    await page.wait_for_timeout(100)
                    cur = await page.evaluate(
                        "() => [...document.querySelectorAll('.sheet-box')]"
                        ".map(e => JSON.stringify(e.getBoundingClientRect())).join()"
                    )
                    if cur and cur == last:
                        return
                    last = cur

            # remote controls over the data channel
            await watch.get_by_role("button", name="More").click()
            await settle(watch)
            # every tab fits without a scroll; tiles are square and large enough to tap
            shown = 0
            heights = set()
            for tab in ("Picture", "Alerts", "Room"):
                await watch.get_by_role("tab", name=tab).click()
                await watch.wait_for_timeout(150)
                assert await watch.evaluate(NO_SCROLL), f"More sheet scrolls on {tab}"
                heights.add(
                    await watch.evaluate(
                        "Math.round(document.querySelector('dialog[open] .sheet-box')"
                        ".getBoundingClientRect().height)"
                    )
                )
                tiles = watch.locator("[data-tile]:visible")
                for i in range(await tiles.count()):
                    box = await tiles.nth(i).bounding_box()
                    assert box and box["width"] >= 64, box
                    assert abs(box["width"] - box["height"]) < 2, box
                    shown += 1
                await watch.screenshot(path=str(SHOTS / f"watch-more-{tab.lower()}.png"))
                if tab == "Alerts":
                    # headless Chromium cannot grant notifications: the push tile says so
                    await expect(watch.locator("[data-push-row]")).to_have_count(1, timeout=5000)
                    assert "blocked" in await watch.evaluate(
                        "document.querySelector('[data-push-row]').innerText"
                    )
                    for name in ("Crying", "Stirring"):
                        pressed = await watch.get_by_role("button", name=name).get_attribute(
                            "aria-pressed"
                        )
                        assert pressed == "true", name
            assert shown >= 12, shown
            assert len(heights) == 1, f"More sheet changes size: {heights}"
            await watch.get_by_role("tab", name="Picture").click()
            await watch.get_by_role("button", name="Switch camera").click()
            await cam.wait_for_function("() => app.rtc.facing === 'user'", timeout=5000)
            print("flip relayed")
            sound = watch.get_by_role("button", name="Sound only", exact=True)
            await sound.click()
            assert await sound.get_attribute("aria-pressed") == "true"
            # the cam drops the video sender for that viewer to null
            await cam.wait_for_function(
                "() => Object.values(app.rtc.pcs).length > 0 &&"
                " Object.values(app.rtc.pcs).every("
                "  p => p.pc._vsender && p.pc._vsender.track === null)",
                timeout=5000,
            )
            # and decoded frames on the viewer stop growing
            frames = (
                "async () => { let n = 0;"
                " for (const p of Object.values(app.rtc.pcs)) {"
                "  const s = await p.pc.getStats();"
                "  s.forEach(r => {"
                "   if (r.type === 'inbound-rtp' && r.kind === 'video')"
                "    n = r.framesDecoded ?? n;"
                "  });"
                " }"
                " return n; }"
            )
            f1 = await watch.evaluate(frames)
            await watch.wait_for_timeout(2000)
            f2 = await watch.evaluate(frames)
            # a frame already in flight can still decode; a live feed adds ~60
            assert f2 - f1 <= 2, (f1, f2)
            print("sound only stops video")
            await watch.screenshot(path=str(SHOTS / "watch-sound-only.png"))
            await watch.get_by_role("button", name="Sound only", exact=True).click()
            await cam.wait_for_function(
                "() => Object.values(app.rtc.pcs).every("
                "  p => p.pc._vsender && p.pc._vsender.track !== null)",
                timeout=5000,
            )
            await watch.wait_for_timeout(1500)
            f3 = await watch.evaluate(frames)
            assert f3 > f2, (f2, f3)
            print("video back")
            await watch.keyboard.press("Escape")
            await settle(watch)

            # attention: Screen off tells the cam nobody looks → no video at all
            await watch.get_by_role("button", name="Screen off").click()
            await cam.wait_for_function(
                "() => Object.values(app.rtc.pcs).every("
                "  p => p.pc._vsender && p.pc._vsender.track === null)",
                timeout=8000,
            )
            f1 = await watch.evaluate(frames)
            await watch.wait_for_timeout(2000)
            f2 = await watch.evaluate(frames)
            assert f2 - f1 <= 2, (f1, f2)
            print("screen off stops video")
            await watch.mouse.click(195, 422)  # a tap wakes the dim screen
            await cam.wait_for_function(
                "() => Object.values(app.rtc.pcs).every("
                "  p => p.pc._vsender && p.pc._vsender.track !== null)",
                timeout=5000,
            )
            woke = await watch.evaluate(frames)
            await watch.wait_for_function(
                f"async () => (await ({frames})()) > {woke}", timeout=5000
            )
            print("picture back after wake")
            await cam.wait_for_function(
                "() => Object.values(app.rtc.pcs).every("
                "  p => p.pc._vsender.getParameters().encodings[0].maxFramerate === 24)",
                timeout=8000,
            )
            await watch.wait_for_timeout(2000)
            fps = await cam.evaluate(out_fps)
            assert fps >= 15, fps
            print("looking again cam fps:", fps)

            # feed-driven unit checks: speech is not a cry, the crying
            # cooldown holds, stirring needs motion and sound together,
            # a luma jump flips the lights
            cry0 = await cam.evaluate("app.rtc.events.filter(e => e.kind === 'crying').length")
            await cam.evaluate(
                "(() => { const T = performance.now(); for (let i = 0; i < 40; i++)"
                " app.rtc.detect.feed({level: -45, f0: 150, clarity: 0.8, band: 0.8,"
                "  motion: false, luma: 100, t: T + i * 100}); })()"
            )
            cry1 = await cam.evaluate("app.rtc.events.filter(e => e.kind === 'crying').length")
            assert cry1 == cry0, (cry0, cry1)
            # the same cry inside the 2 min cooldown emits nothing new
            await cam.evaluate(
                "(() => { const T = performance.now(); for (let i = 0; i < 40; i++)"
                " app.rtc.detect.feed({level: -45, f0: 400, clarity: 0.8, band: 0.8,"
                "  motion: false, luma: 100, t: T + i * 100}); })()"
            )
            cry2 = await cam.evaluate("app.rtc.events.filter(e => e.kind === 'crying').length")
            assert cry2 == cry0, (cry0, cry2)
            # a clean slate for the stirring and lights checks — feeds share
            # the luma and span buffers on the same clock
            await cam.evaluate("app.rtc.detect.reset()")
            await cam.evaluate(
                "(() => { const T = performance.now(); for (let i = 0; i < 250; i++)"
                " app.rtc.detect.feed({level: 10, f0: 0, clarity: 0, band: 0,"
                "  motion: i < 120, luma: 100, t: T + i * 100}); })()"
            )
            kinds = await cam.evaluate("app.rtc.events.map(e => e.kind)")
            assert "stirring" in kinds, kinds
            await cam.evaluate("app.rtc.detect.reset()")
            await cam.evaluate(
                "(() => { const T = performance.now(); for (let i = 0; i < 250; i++)"
                " app.rtc.detect.feed({level: -80, f0: 0, clarity: 0, band: 0,"
                "  motion: false, luma: i < 120 ? 100 : 170, t: T + i * 100}); })()"
            )
            kinds = await cam.evaluate("app.rtc.events.map(e => e.kind)")
            assert "lights_on" in kinds, kinds
            # a long cry re-fires after its cooldown: the floor stays frozen
            await cam.evaluate("app.rtc.detect.reset()")
            n0 = await cam.evaluate("app.rtc.events.filter(e => e.kind === 'crying').length")
            await cam.evaluate(
                "(() => { const T = performance.now(); for (let i = 0; i < 140; i++)"
                " app.rtc.detect.feed({level: -45, f0: 400, clarity: 0.8, band: 0.8,"
                "  motion: false, luma: 100, t: T + i * 1000}); })()"
            )
            n1 = await cam.evaluate("app.rtc.events.filter(e => e.kind === 'crying').length")
            assert n1 == n0 + 2, (n0, n1)
            print("long cry re-fires after the cooldown")

            # push to talk: the camera hears the viewer's fake mic
            await watch.get_by_role("button", name="Talk").hover()
            await watch.mouse.down()
            await cam.wait_for_selector("text=Talking", timeout=6000)
            # talk mutes internally, so "Turn on sound" must stay hidden
            assert not await watch.get_by_role("button", name="Turn on sound").is_visible()
            await cam.screenshot(path=str(SHOTS / "cam-talking.png"))
            await watch.screenshot(path=str(SHOTS / "watch-talking.png"))
            print("talk-back heard on cam")
            await watch.mouse.up()

            if await cam.evaluate("() => !!navigator.getBattery"):
                await watch.wait_for_function(
                    "() => app.rtc.battery && app.rtc.battery.level !== undefined",
                    timeout=5000,
                )
                lvl = await watch.evaluate("() => app.rtc.battery.level")
                print("battery relayed:", lvl)
            else:
                print("getBattery unavailable; battery check skipped")
            pill = await watch.locator("text=Live").first.inner_text()
            assert pill.startswith("Live"), pill
            # the picture view: the whole screen, the dock hides while it plays
            await watch.get_by_role("button", name="Picture", exact=True).click()
            assert (
                await watch.evaluate("document.querySelector('#watch').dataset.mode") == "picture"
            )
            await watch.wait_for_timeout(4500)
            await watch.screenshot(path=str(SHOTS / "watch-live-chrome-hidden.png"))
            # the top bar and its meters stay in view
            assert await watch.locator("header [data-motion-meter]").is_visible()
            await watch.mouse.click(195, 600)
            await watch.get_by_role("button", name="Glance", exact=True).click()
            assert await watch.evaluate("document.querySelector('#watch').dataset.mode") == "glance"

            # the cam may have dimmed during the checks: tap to wake, then Viewers
            await cam.mouse.click(195, 300)
            try:
                await cam.wait_for_selector(".lights-out", state="hidden", timeout=3000)
            except Exception:
                pass
            await cam.get_by_role("button", name="Viewers").click()
            await cam.wait_for_timeout(600)
            await cam.screenshot(path=str(SHOTS / "cam-viewers-sheet.png"))
            await cam.keyboard.press("Escape")

            lonely = await cam_ctx.new_page()
            await lonely.goto(f"{base}/watch/000000")
            await lonely.wait_for_timeout(500)
            await lonely.screenshot(path=str(SHOTS / "watch-waiting.png"))
            await lonely.close()

            assert "1 watching" in await cam.inner_text("body")
            print("cam: shows 1 watching")

            # the cam may have dimmed during the checks: wake it before Viewers
            await cam.mouse.click(195, 300)
            try:
                await cam.wait_for_selector(".lights-out", state="hidden", timeout=3000)
            except Exception:
                pass

            ios = await browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
                    " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0"
                    " Mobile/15E148 Safari/604.1"
                ),
            )
            iphone = await ios.new_page()
            await iphone.goto(base)
            await iphone.wait_for_timeout(800)
            assert "Add to Home Screen" in await iphone.inner_text("body")
            await iphone.screenshot(path=str(SHOTS / "home-ios-install.png"))
            print("ios install hint shown")
            await iphone.close()

            # a reconnecting viewer gets the missed events
            await watch.reload()
            await watch.wait_for_function(
                "() => document.querySelector('[data-last-event]')?.textContent.trim()",
                timeout=25000,
            )
            print("reconnected viewer got the event backlog")

            # Tonight: inject an 8h night on the cam, ask for it on the viewer
            stir_m = await cam.evaluate(
                "(() => { const base = Math.floor(Date.now() / 60000) - 8 * 60;"
                " const items = [];"
                " for (let i = 0; i < 480; i++) {"
                "  const b = {m: base + i, peak: 5, sound: 6, motion: 2, ev: []};"
                "  if (i === 300) b.ev = ['stirring'];"
                "  if (i === 330) { b.ev = ['crying']; b.peak = 30; b.sound = 55; }"
                "  items.push(b);"
                " }"
                " app.rtc.timeline.add(items); app.rtc.timeline.flush();"
                " return items[300].m; })()"
            )
            stored = await cam.evaluate(
                "JSON.parse(localStorage.getItem('philomena.timeline.'"
                " + document.querySelector('#cam').dataset.code)).length"
            )
            assert stored >= 480, stored
            await watch.get_by_role("button", name="More").click()
            await settle(watch)
            await watch.get_by_role("button", name="Tonight").click()
            await watch.wait_for_function(
                "() => document.querySelector('#tonight')._titems !== undefined",
                timeout=10000,
            )
            got = await watch.evaluate("document.querySelector('#tonight')._titems.length")
            # 480 injected + the live bucket the camera records right now
            assert 480 <= got <= 484, got
            print("tonight got", got, "buckets over chunked sends")
            quiet = await watch.evaluate("document.querySelector('#tonight').innerText")
            assert "Stirred at" in quiet and "Cried at" in quiet, quiet
            stir_time = await cam.evaluate(
                "(() => { const d = new Date(" + str(stir_m) + " * 60000);"
                " return String(d.getHours()).padStart(2,'0') + ':'"
                " + String(d.getMinutes()).padStart(2,'0'); })()"
            )
            assert stir_time in quiet, (stir_time, quiet)
            px = await watch.evaluate(
                "(() => { const c = document.querySelector('#tonight canvas');"
                " const g = c.getContext('2d');"
                " const d = g.getImageData(0, 0, c.width, c.height).data;"
                " let s = 0; for (let i = 3; i < d.length; i += 400) s += d[i];"
                " return s; })()"
            )
            assert px > 0, "canvas is blank"
            await settle(watch)
            await watch.screenshot(path=str(SHOTS / "watch-tonight.png"))
            await watch.keyboard.press("Escape")
            await settle(watch)
            print("tonight sheet ok")

            # camera name: set on the cam, seen on the viewer top bar
            await cam.evaluate(
                "fetch('/cam/" + code + "/name', {method: 'POST',"
                " headers: {'content-type': 'application/json'},"
                " body: JSON.stringify({name: 'Nursery'})})"
            )
            await watch.wait_for_function(
                "document.body.innerText.includes('Nursery')", timeout=10000
            )
            await watch.screenshot(path=str(SHOTS / "watch-named.png"))
            print("camera name shown on the viewer")

            # your cameras on home, in the viewer's context
            home = await watch_ctx.new_page()
            await home.goto(base)
            await home.wait_for_function(
                "document.body.innerText.includes('Your cameras')", timeout=10000
            )
            assert "Nursery" in await home.inner_text("body")
            await home.screenshot(path=str(SHOTS / "home-your-cameras.png"))
            await home.close()
            print("home shows your cameras")

            # brighten: More sheet toggle applies the CSS filter
            await watch.get_by_role("button", name="More").click()
            await settle(watch)
            await watch.get_by_role("tab", name="Picture").click()
            await watch.get_by_role("button", name="Brighten", exact=True).click()
            filt = await watch.evaluate(
                "getComputedStyle(document.querySelector('[data-rtc=remote]').parentElement"
                " || document.body).filter"
            )
            await watch.keyboard.press("Escape")
            await settle(watch)
            filt = await watch.evaluate("getComputedStyle(document.querySelector('video')).filter")
            assert "brightness(1.6)" in filt, filt
            print("brighten applies the filter")

            # pinch: drive two pointer events apart (CDP touch does not reach
            # pointer handlers in this Chromium build)
            await watch.evaluate(
                """(() => {
                const el = document.querySelector('[data-view]');
                const ev = (type, id, x, y) => el.dispatchEvent(
                    new PointerEvent(type, {pointerId: id, clientX: x,
                        clientY: y, bubbles: true}));
                ev('pointerdown', 11, 170, 400);
                ev('pointerdown', 12, 220, 400);
                ev('pointermove', 11, 120, 400);
                ev('pointermove', 12, 280, 400);
                ev('pointerup', 11, 120, 400);
                ev('pointerup', 12, 280, 400);
            })()"""
            )
            await watch.wait_for_timeout(300)
            t = await watch.evaluate("document.querySelector('[data-view]').style.transform")
            import re as _re

            m = _re.search(r"scale\((\d+(\.\d+)?)\)", t)
            assert m and float(m.group(1)) > 1.5, t
            await watch.screenshot(path=str(SHOTS / "watch-zoomed.png"))
            print("pinch zoom:", t)

            # double-tap on a zoomed picture settles back to 1
            await watch.evaluate(
                """(() => {
                const el = document.querySelector('[data-view]');
                const tap = () => {
                    el.dispatchEvent(new PointerEvent('pointerdown',
                        {pointerId: 21, clientX: 195, clientY: 400, bubbles: true}));
                    el.dispatchEvent(new PointerEvent('pointerup',
                        {pointerId: 21, clientX: 195, clientY: 400, bubbles: true}));
                };
                tap(); tap();
            })()"""
            )
            await watch.wait_for_timeout(400)
            t2 = await watch.evaluate("document.querySelector('[data-view]').style.transform")
            m2 = _re.search(r"scale\((\d+(\.\d+)?)\)", t2)
            assert m2 and float(m2.group(1)) == 1.0, t2
            print("double-tap reset:", t2)

            # the service worker shows a notification for a pushed event
            cdp = await watch.context.new_cdp_session(watch)
            regs = []

            def _on_regs(params):
                regs.extend(params.get("registrations", []))

            cdp.on("ServiceWorker.workerRegistrationUpdated", _on_regs)
            await cdp.send("ServiceWorker.enable")
            await watch.wait_for_timeout(800)
            if regs:
                await cdp.send(
                    "ServiceWorker.deliverPushMessage",
                    {
                        "origin": base,
                        "registrationId": regs[0]["registrationId"],
                        "data": json.dumps(
                            {"title": "Philomena", "kind": "crying", "at": 1, "url": "/w"}
                        ),
                    },
                )
                await watch.wait_for_function(
                    "async () => (await (await navigator.serviceWorker.getRegistration())"
                    ".getNotifications()).length > 0",
                    timeout=10000,
                )
                print("sw push notification shown")
            else:
                print("no service worker registration; sw push check skipped")

            # day: the look switch overrides the phone setting and survives a reload
            await watch.evaluate("app.theme.set('day')")
            assert await watch.evaluate("document.documentElement.dataset.theme") == "day"
            bg = await watch.evaluate("getComputedStyle(document.body).backgroundColor")
            assert bg == "rgb(255, 255, 255)", bg
            # a lit dock pad keeps its icon and label on its dark fill
            sound = watch.locator('[data-part="dock"] > button', has_text="Sound")
            if await sound.get_attribute("aria-pressed") != "true":
                await sound.click()
            await watch.wait_for_selector('[data-part="dock"] > .dock-active')
            pad = await watch.evaluate(
                "(() => { const b = document.querySelector('[data-part=\"dock\"] > .dock-active');"
                " const svg = [...b.querySelectorAll('svg')].find((s) => s.getClientRects().length);"
                " const c = (el) => getComputedStyle(el);"
                " return {bg: c(b).backgroundColor, icon: c(svg).color,"
                " label: c(b.querySelector('.dock-label')).color}; })()"
            )
            assert pad["icon"] != pad["bg"], pad
            assert pad["label"] != pad["bg"], pad
            assert pad["icon"] == "rgb(255, 255, 255)", pad
            await watch.wait_for_timeout(400)
            await watch.screenshot(path=str(SHOTS / "watch-day.png"))
            await watch.set_viewport_size({"width": 375, "height": 667})
            await watch.wait_for_timeout(300)
            await watch.screenshot(path=str(SHOTS / "watch-day-small.png"))
            await watch.set_viewport_size({"width": 390, "height": 844})
            await watch.get_by_role("button", name="Picture", exact=True).click()
            await watch.wait_for_timeout(400)
            await watch.screenshot(path=str(SHOTS / "watch-day-picture.png"))
            await watch.get_by_role("button", name="Glance", exact=True).click()
            day_home = await watch_ctx.new_page()
            await day_home.goto(base)
            assert await day_home.evaluate("document.documentElement.dataset.theme") == "day"
            await day_home.screenshot(path=str(SHOTS / "home-day.png"))
            await day_home.get_by_role("button", name="Auto", exact=True).click()
            assert await day_home.evaluate("document.documentElement.dataset.theme") == "night"
            await day_home.close()
            print("day look and auto both apply")

            print("waiting for auto lights-out (up to 40 s; re-dim is 30 s)…")
            await cam.wait_for_selector(".lights-out", state="visible", timeout=40000)
            await cam.wait_for_timeout(400)
            await cam.screenshot(path=str(SHOTS / "cam-lights-out.png"))
            print("lights-out reached")

            # closing the camera rings the lost-connection alarm
            await cam.close()
            await watch.wait_for_selector("text=No connection to the camera", timeout=25000)
            await watch.screenshot(path=str(SHOTS / "watch-alarm.png"))
            print("alarm banner shown")
            await browser.close()

            # a still scene drops the cam to the calm rate
            write_still("/tmp/philomena-still.y4m")
            browser = await p.chromium.launch(
                args=[
                    "--use-fake-device-for-media-stream",
                    "--use-fake-ui-for-media-stream",
                    "--disable-dev-shm-usage",
                    "--use-file-for-fake-video-capture=/tmp/philomena-still.y4m",
                ]
            )
            cam_ctx = await browser.new_context(
                viewport={"width": 390, "height": 844},
                permissions=["camera", "microphone"],
            )
            cam = await cam_ctx.new_page()
            await cam.goto(base)
            await cam.get_by_role("button", name="Stays with the baby").click()
            await cam.wait_for_url("**/cam/*")
            code = cam.url.rsplit("/", 1)[-1]
            watch_ctx = await browser.new_context(
                viewport={"width": 390, "height": 844},
                has_touch=True,
                permissions=["camera", "microphone", "notifications"],
            )
            watch = await watch_ctx.new_page()
            await watch.goto(f"{base}/watch/{code}")
            await cam.get_by_role("button", name="Allow").click()
            await cam.wait_for_function(
                "() => Object.values(app.rtc.pcs).length > 0 && app.rtc.motion",
                timeout=20000,
            )
            await cam.evaluate("app.rtc.motion.calmAfter = 2")
            await cam.wait_for_function("() => app.rtc.motionLevel === 'calm'", timeout=10000)
            await cam.wait_for_function(
                "() => Object.values(app.rtc.pcs).every("
                "  p => p.pc._vsender.getParameters().encodings[0].maxFramerate === 6)",
                timeout=8000,
            )
            await cam.wait_for_timeout(2000)
            fps = await cam.evaluate(out_fps)
            print("still cam fps:", fps)
            await browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)
    print("screenshots in", SHOTS)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
