"""Persistent rooms, viewer devices, and approvals (SQLite via litewriter).

Secrets never reach the table: rooms keep a sha256 of the cam key and
devices keep a sha256 of the device token. A stale `last_seen_at` means
the camera phone stopped opening the room; `prune` drops those rooms.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass

from litewriter import Tx
from stario.json import dumps as json_dumps

ROOM_STALE_SECONDS = 30 * 24 * 3600
PENDING_CAP = 5


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


ROOM_COLUMNS = {
    "cam_key_hash": "TEXT AS (data->>'cam_key_hash')",
    "created_at": "REAL AS (data->>'created_at')",
    "last_seen_at": "REAL AS (data->>'last_seen_at')",
}
DEVICE_COLUMNS = {
    "token_hash": "TEXT AS (data->>'token_hash')",
    "name": "TEXT AS (data->>'name')",
}
APPROVAL_COLUMNS = {
    "code": "TEXT AS (data->>'code')",
    "device_id": "TEXT AS (data->>'device_id')",
    "status": "TEXT AS (data->>'status')",
    "created_at": "REAL AS (data->>'created_at')",
}


def schema(tx: Tx) -> None:
    tx.execute(
        "CREATE TABLE IF NOT EXISTS rooms ("
        " id TEXT PRIMARY KEY, data TEXT NOT NULL CHECK (json_valid(data)))"
    )
    tx.execute(
        "CREATE TABLE IF NOT EXISTS devices ("
        " id TEXT PRIMARY KEY, data TEXT NOT NULL CHECK (json_valid(data)))"
    )
    tx.execute(
        "CREATE TABLE IF NOT EXISTS approvals ("
        " id INTEGER PRIMARY KEY, data TEXT NOT NULL CHECK (json_valid(data)))"
    )
    for table, columns in (
        ("rooms", ROOM_COLUMNS),
        ("devices", DEVICE_COLUMNS),
        ("approvals", APPROVAL_COLUMNS),
    ):
        have = {row[0] for row in tx.query(f"SELECT name FROM pragma_table_xinfo('{table}')")}
        for name, column in columns.items():
            if name not in have:
                tx.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column} VIRTUAL")
    tx.execute("CREATE INDEX IF NOT EXISTS rooms_last_seen ON rooms(last_seen_at)")
    tx.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS approvals_code_device ON approvals(code, device_id)"
    )
    tx.execute("CREATE INDEX IF NOT EXISTS approvals_code ON approvals(code, status)")


# --- rooms -----------------------------------------------------------------


def add_room(tx: Tx, code: str, cam_key_hash: str) -> None:
    tx.execute(
        "INSERT INTO rooms (id, data) VALUES (:id, :data)",
        id=code,
        data=json_dumps(
            {
                "cam_key_hash": cam_key_hash,
                "created_at": time.time(),
                "last_seen_at": time.time(),
            }
        ),
    )


def room_row(db, code: str) -> tuple | None:
    return db.one("SELECT id, cam_key_hash FROM rooms WHERE id = :code", code=code)


def delete_room(tx: Tx, code: str) -> None:
    tx.execute("DELETE FROM approvals WHERE code = :code", code=code)
    tx.execute("DELETE FROM rooms WHERE id = :code", code=code)


def touch_room(tx: Tx, code: str) -> None:
    tx.execute(
        "UPDATE rooms SET data = json_set(data, '$.last_seen_at', :now) WHERE id = :code",
        code=code,
        now=time.time(),
    )


def prune_rooms(tx: Tx, now: float | None = None) -> None:
    cutoff = (now or time.time()) - ROOM_STALE_SECONDS
    tx.execute(
        "DELETE FROM approvals WHERE code IN (SELECT id FROM rooms WHERE last_seen_at < :c)",
        c=cutoff,
    )
    tx.execute("DELETE FROM rooms WHERE last_seen_at < :c", c=cutoff)


# --- devices ---------------------------------------------------------------


def add_device(tx: Tx, device_id: str, token_hash: str, name: str) -> None:
    tx.execute(
        "INSERT INTO devices (id, data) VALUES (:id, :data)",
        id=device_id,
        data=json_dumps({"token_hash": token_hash, "name": name}),
    )


def device_row(db, device_id: str) -> tuple | None:
    return db.one("SELECT id, token_hash, name FROM devices WHERE id = :id", id=device_id)


def set_device_name(tx: Tx, device_id: str, name: str) -> None:
    tx.execute(
        "UPDATE devices SET data = json_set(data, '$.name', :name) WHERE id = :id",
        id=device_id,
        name=name,
    )


def new_device(tx: Tx, name: str) -> tuple[str, str]:
    device_id = secrets.token_hex(8)
    token = secrets.token_urlsafe(32)
    add_device(tx, device_id, hash_secret(token), name)
    return device_id, token


# --- approvals -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Approval:
    device_id: str
    status: str
    name: str
    created_at: float


def approval_status(db, code: str, device_id: str) -> str | None:
    row = db.one(
        "SELECT status FROM approvals WHERE code = :code AND device_id = :did",
        code=code,
        did=device_id,
    )
    return row[0] if row else None


def approvals_for(db, code: str) -> list[Approval]:
    return db.query(
        "SELECT a.device_id, a.status, d.name, a.created_at"
        " FROM approvals a JOIN devices d ON d.id = a.device_id"
        " WHERE a.code = :code"
        " ORDER BY a.status = 'pending' DESC, a.created_at",
        Approval,
        code=code,
    )


def approval_devices(db, code: str) -> list[str]:
    return [r[0] for r in db.query("SELECT device_id FROM approvals WHERE code = :code", code=code)]


def upsert_pending(tx: Tx, code: str, device_id: str) -> bool:
    """Insert a pending approval when none exists. Returns True for a new knock."""
    exists = tx.one(
        "SELECT status FROM approvals WHERE code = :code AND device_id = :did",
        code=code,
        did=device_id,
    )
    if exists:
        return False
    tx.execute(
        "INSERT INTO approvals (data) VALUES (:data)",
        data=json_dumps(
            {"code": code, "device_id": device_id, "status": "pending", "created_at": time.time()}
        ),
    )
    rows = tx.query(
        "SELECT id FROM approvals WHERE code = :code AND status = 'pending'"
        " ORDER BY created_at DESC",
        code=code,
    )
    for row in rows[PENDING_CAP:]:
        tx.execute("DELETE FROM approvals WHERE id = :id", id=row[0])
    return True


def approve(tx: Tx, code: str, device_id: str) -> None:
    tx.execute(
        "UPDATE approvals SET data = json_set(data, '$.status', 'approved')"
        " WHERE code = :code AND device_id = :did",
        code=code,
        did=device_id,
    )


def remove_approval(tx: Tx, code: str, device_id: str) -> None:
    tx.execute(
        "DELETE FROM approvals WHERE code = :code AND device_id = :did",
        code=code,
        did=device_id,
    )


def set_room_name(tx: Tx, code: str, name: str) -> None:
    tx.execute(
        "UPDATE rooms SET data = json_set(data, '$.name', :name) WHERE id = :code",
        name=name,
        code=code,
    )


def room_name(db, code: str) -> str:
    row = db.one("SELECT data->>'name' FROM rooms WHERE id = :code", code=code)
    return row[0] if row and row[0] else ""


def cameras_of(db, device_id: str) -> list[tuple]:
    """Approved rooms for a device: (code, name) pairs."""
    return db.query(
        "SELECT a.code, r.data->>'name' FROM approvals a"
        " JOIN rooms r ON r.id = a.code"
        " WHERE a.device_id = :did AND a.status = 'approved'"
        " ORDER BY a.created_at",
        did=device_id,
    )
