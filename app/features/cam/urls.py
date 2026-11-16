from stario import Route

CAM = Route("GET /cam/{code}")
CAM_LIVE = Route("GET /cam/{code}/live")
CAM_NEW_CODE = Route("POST /cam/{code}/new-code")
CAM_APPROVE = Route("POST /cam/{code}/viewers/{device_id}/approve")
CAM_REMOVE = Route("POST /cam/{code}/viewers/{device_id}/remove")
CAM_NAME = Route("POST /cam/{code}/name")
