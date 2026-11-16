# Stario app guide

How to build a Stario app, unless the developer asks for something else.

Stario is Python hypermedia. A handler writes HTML. Datastar morphs it into the page. One open SSE response keeps a page live. State lives on the server. Docs: https://stario.dev/docs.

The last section of this file holds the notes of this app, under 4 KB. A deep note on one topic goes in its own file, named by a line such as "Read `EDITOR.md` before you change the editor."

## Which skill

Read the one skill for the task in `.agents/skills/`, then write the code. `stario-create add <kit>` writes tested files.

- A static page (no command): no skill. Write `urls.py`, `views.py`, and a page class with one `show`.
- A page that every tab sees change, in SQLite: `stario-feature` and `stario-litewriter`.
- State in memory, a message to one tab, an edit dialog: `stario-relay`.
- A sort, a filter, paging, a search as you type: `stario-view`.
- Work that takes seconds, or a loop on a timer: `stario-jobs`.
- Login: `stario-auth`. Styles: `stario-tailwind-daisyui`. JavaScript: `stario-client`.
- Before a browser or a screenshot: `stario-browser-check`.
- `stario-api` lists every signature. Read it only for a name that the skill and the code do not show.

## Layout

```text
app/
  main.py           bootstrap: shared objects, one register line per page under `# pages`
  config.py         Config: one field with a default per setting; from_env reads it by name
  common/shell.py   page(title, body): the <html> document
  features/<page>/  urls.py (Routes, the View), views.py (render), handlers.py (the page class), data.py (SQL)
  <name>/           code with no URL; never imports features/
tests/test_<page>.py
```

- A page is one folder, named after the URL noun: `/rooms/{room_id}` → `room`. It gets one line in `LINKS` in `app/features/home/views.py`.
- A feature may import the `urls.py` and `data.py` of another feature, never its views or handlers.
- JavaScript lives in `static/js/<name>.js` as `app.<name>`, never in a Python string.

## Stario rules

- Not ASGI: no Uvicorn, FastAPI, or response objects.
- `bootstrap(app, span)` is an async generator with one `yield`. Keep `app.use("/", same_origin(), security_headers())`. `same_origin()` is the CSRF guard: add no CSRF tokens. It does not check GET, so a GET never changes state.
- A handler is `async def (c: Context, w: Writer) -> None`. It answers once: `w.html`, `w.text`, `w.empty`, `w.redirect`, or `SSE(w)`.
- `Route("GET /rooms/{room_id}")` is one method on one path; a GET route answers HEAD too. `app.add(ROUTE, handler)`; `ROUTE.href(room_id, query={...})`. No `url_for`.
- A stream loop iterates `c.alive(source)`. Background work is `c.app.create_task(coro)`. A timer loop waits on `app.shutdown`, never `asyncio.sleep`.
- No module-level state. No `os.environ` outside `config.py`. JSON goes through `stario.json`.
- A middleware with a dependency is a method of a class built in `bootstrap`: `app.use("/", session.attach)`, never a function that returns a middleware. Handlers read its state through a typed function such as `current_user(c)`, not `c.state[...]`.

## A page is a resource

- **Go somewhere** (a page, a sort, a filter): `<a href>`. The query holds the view.
- **A result only this tab needs** (search as you type): a `GET` that answers `SSE(w).patch_elements(part)`.
- **Change state**: a command, `POST`.

A page on state that cannot change while it is open is static: `w.html(render(...))`. A page on shared state is live:

```text
GET  /board        the document; its top element has data.init(at.get(BOARD_LIVE.href(), retry="always"))
GET  /board/live   the stream: send render(...), and again after each change
POST /board/...    a command
```

The stream is the only thing that sends HTML. It follows `db.watch(query)` (SQLite) or `relay.subscribe(CHANGED, latest=True)` (memory). A command never answers with HTML:

1. Read: `await read_signals(c.req)`, `c.match.params`. A plain HTML form or a file upload: `await read_form(c.req)` (`stario.forms`). A body over 10 MiB needs `max_size=`.
2. Validate: bad input gets `w.text("why", status=400)` and `return`.
3. Reply: `w.empty()`, `SSE(w).patch_signals(...)`, or `SSE(w).navigate(url)`.
4. Execute: `await db.write(...)`, or change memory, then `relay.publish(CHANGED, {})`.

## Render and signals

- `render(...)` returns the whole document from state. It does not fetch.
- The element with `data.init(...)` and `data.signals({...}, if_missing=True)` keeps its tag, `id`, and attributes in every render.
- Signals carry what the user types or picks. A leading `_` keeps a signal in the tab. One signal per field, not one per row.
- A busy form: `data.indicator("_saving")` on the `<form>`, `data.attr("disabled", "$_saving")` on its button.
- A `<dialog>` or `<details>` keeps `data.preserve_attr("open")`.

## Code shape

A page is one class in `handlers.py`. Its fields are its dependencies. A read or a write is a function in `data.py`: `list_*`, `get_*`, `add_*`, `set_*`, `remove_*`.

```python
@dataclass(frozen=True, slots=True)
class BoardPage:
    db: LiteWriter
    relay: Relay[dict]

    def register(self, app: App) -> None:
        app.add(BOARD, self.show)

    async def show(self, c: Context, w: Writer) -> None:
        view = BoardView.from_query(c.req.query)
        w.html(render(list_tiles(self.db, view), view))
```

No service classes, repositories, base pages, `utils`, or helpers with one call site. Read input like this:

```python
title = str(signals.get("title", "")).strip()  # text
done = signals.get("done") is True  # bool
tile_id = c.match.params["tile_id"]  # path int: tile_id.isdecimal(), then int(tile_id)
```

## Tests

Tests run `TestClient(bootstrap, request_timeout=5)`. Each page: it loads, a command repaints the stream, bad input gets 4xx. The next SSE event is the changed HTML; two streams are two tabs. A `GET` sends signals in `params={"datastar": '{"q": "x"}'}`, a `POST` in `json=`. `tests/test_pages.py` finds and checks every page by itself.

A bug starts with a test that shows it. Run `just test -k <name>` and see it fail. Then fix, see it pass, and read `git diff`.

## Checks

Change a file with the Edit tool. Run Python as `uv run python`. Run `just check` after each change: it formats, fixes lint, checks types, runs the tests, and prints only problems. pyrefly checks each call, so trust Stario, Datastar, and litewriter.

A browser is only for client JS that holds state. No computer use. When the user watches the app, the user is the browser: say what to look at. When it does not work: `curl` their server, then a failing test (skill `stario-browser-check`).

## Cursor Cloud specific instructions

Install is `.cursor/cloud-install.sh`.

## This app

Philomena is a baby monitor. One phone is the camera; other phones (or laptops) watch over WebRTC. There is no login. A 6-digit code joins a camera with its viewers. A device cookie makes one phone the camera owner, and the camera approves each viewer. Rooms, approvals, and push subscriptions live in SQLite (`data/philomena.sqlite3`, litewriter).

Design brief and style system (no daisyUI): `DESIGN.md`. Read it before a visual change.

Stario has no WebSocket, so signaling is SSE plus POST. `app/rooms/` keeps the room registry in memory (`Rooms`, `Room(cam, viewers)`) and `ice_servers(config)` for STUN/TURN. One `Relay[dict]` carries every message to a tab on subject `peer.{tab}`; each live stream subscribes before it registers, then replies to relay messages with `sse.execute_script(receive_script(msg))` — `app.rtc.receive(...)` in `static/js/rtc.js`, never `patch_signals` (ICE candidates must not coalesce).

Routes: `GET /` landing, `POST /cam` (new code, `SSE.navigate` to the cam page), `GET /watch` (validates `code`), `GET /cam/{code}` + `GET /cam/{code}/live`, `GET /watch/{code}` + `GET /watch/{code}/live`, `POST /rooms/{code}/signal` (`{tab, to, kind, data}`; cam↔viewer only). `GET /manifest.webmanifest`, `GET /sw.js` (root scope), `GET /health` are the `pwa` feature.

Config keys (`app/config.py`): `STUN_URLS`, `TURN_URLS` (comma lists), `COTURN_STATIC_AUTH_SECRET` (TURN HMAC secret), `TURN_PUBLIC_IP` (coturn only), `TURN_TTL` (default 86400), `PUBLIC_URL` (the HTTPS address of the install, default `http://localhost:8000`; the base for link-preview images and the Web Push `sub` claim). Philomena is self-hosted: docs and tests use `monitor.example.com` and `203.0.113.10`, never a real host. TURN is only announced when both `TURN_URLS` and the secret are set.

Phones require HTTPS for camera, microphone, and wake lock, so the app must run behind a TLS host — plain `just dev` on a LAN IP will not get media on a phone.

`scripts/e2e.py` is the browser check: `uv run --with playwright python scripts/e2e.py` pairs a fake camera and viewer over WebRTC and saves screenshots to `/tmp/philomena-shots/`. It runs `just css` first and is not part of `just check`.

Web Push: the camera posts events to `POST /cam/{code}/events`; the server fans them out to the room's push subscriptions (`push_subs` table) after per-kind cooldowns and a 6/minute cap, and pushes `offline` when the cam stream is gone for `OFFLINE_PUSH_AFTER` s (default 60). VAPID is generated once into `data/vapid.pem` (0600) — no env needed. Endpoints are allowlisted (FCM, Apple, Mozilla, Windows). iOS needs Home Screen install for notifications.

iOS may stop web audio when the screen locks or the app goes to the background. The viewer phone must stay on the page (wake lock, or the "Screen off" mode).

Adaptive video: the camera measures motion from its preview (`app.motion`) and sends at 24 fps when `active`, 6 fps when `calm` (10 s), and 2 fps when `still` (60 s). `app.motion` ignores a brightness shift of the whole frame and pixel changes below 4 times the noise floor of the room, so grain in a dark room is not motion. A viewer that reports away (hidden, Screen off, or Sound only) gets no video track at all; the camera puts the track back when it looks again. `maxFramerate` and `applyConstraints` support differs per browser; the bitrate cap works everywhere. Audio always stays at full quality.

### Deploy

`README.md` is the self-hosting guide: what the server stores, the ports, the settings, a deploy with Yard, a deploy with plain Compose and Caddy, backups, and the real-phone test list. Keep it current when a deploy step changes.

Yard deploys `compose.yml`. The `app` service builds `Containerfile` and joins network `yard`. The `turn` service runs coturn 4.18.0 with `network_mode: host`. TURN has no TLS. Caddy cannot proxy UDP TURN traffic, and WebRTC media stays end-to-end DTLS-SRTP through the relay. coturn listens on the public IP only, with relay ports 49160-49199/udp and `denied-peer-ip` on every private range.

