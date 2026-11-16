"""Cookie credentials: `cam` = {code}.{key}, `device` = {device_id}.{token}.

Only sha256 hashes live in the database, so a leaked cookie file does not
reveal room keys and a leaked table does not reveal live tokens.
"""

import hmac
import secrets

from stario import Context, Writer
from stario.cookies import set_cookie

from app.rooms import valid_code
from app.rooms.data import device_row, hash_secret, room_row

CAM_COOKIE = "cam"
DEVICE_COOKIE = "device"
MAX_AGE = 365 * 24 * 3600


def _secure(c: Context) -> bool:
    # Behind Caddy the app sees X-Forwarded-Proto; on a laptop it sees none.
    proto = c.req.headers.get("x-forwarded-proto", "")
    return proto == "https"


def set_cam_cookie(c: Context, w: Writer, code: str, key: str) -> None:
    set_cookie(w, CAM_COOKIE, f"{code}.{key}", max_age=MAX_AGE, secure=_secure(c))


def set_device_cookie(c: Context, w: Writer, device_id: str, token: str) -> None:
    set_cookie(w, DEVICE_COOKIE, f"{device_id}.{token}", max_age=MAX_AGE, secure=_secure(c))


def new_cam_key() -> str:
    return secrets.token_urlsafe(32)


def cam_owner(db, c: Context, code: str) -> bool:
    """True when the cam cookie owns this code's room."""
    raw = c.req.cookies.get(CAM_COOKIE, "")
    cookie_code, _, key = raw.partition(".")
    if cookie_code != code or not key or not valid_code(code):
        return False
    row = room_row(db, code)
    return row is not None and hmac.compare_digest(row[1], hash_secret(key))


def cam_cookie_room(db, c: Context) -> str | None:
    """The code the cam cookie owns, when it owns a room that still exists."""
    raw = c.req.cookies.get(CAM_COOKIE, "")
    code, _, key = raw.partition(".")
    if not (key and valid_code(code)):
        return None
    row = room_row(db, code)
    return code if row is not None and hmac.compare_digest(row[1], hash_secret(key)) else None


def device_of(db, c: Context) -> tuple | None:
    """The device row the device cookie proves, or None."""
    raw = c.req.cookies.get(DEVICE_COOKIE, "")
    device_id, _, token = raw.partition(".")
    if not (device_id.isalnum() and len(device_id) <= 32 and token):
        return None
    row = device_row(db, device_id)
    if row is None or not hmac.compare_digest(row[1], hash_secret(token)):
        return None
    return row


def device_name_from_ua(ua: str) -> str:
    if "iPhone" in ua:
        return "iPhone"
    if "iPad" in ua:
        return "iPad"
    if "Android" in ua:
        return "Android phone"
    if "Windows" in ua:
        return "Windows PC"
    if "Mac" in ua:
        return "Mac"
    return "Phone"
