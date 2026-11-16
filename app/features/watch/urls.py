from stario import Route

WATCH_ROOM = Route("GET /watch/{code}")
WATCH_LIVE = Route("GET /watch/{code}/live")
WATCH_NAME = Route("POST /watch/{code}/name")
