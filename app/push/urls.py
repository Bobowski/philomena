from stario import Route

PUSH_SUB = Route("POST /watch/{code}/push")
PUSH_KINDS = Route("POST /watch/{code}/push/kinds")
PUSH_OFF = Route("POST /watch/{code}/push/off")
CAM_EVENTS = Route("POST /cam/{code}/events")
