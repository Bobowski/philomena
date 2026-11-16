"""Push subscriptions: one row per (code, endpoint), data as JSON."""

import json
import time

from litewriter import Tx

SCHEMA = """
CREATE TABLE IF NOT EXISTS push_subs (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    code TEXT GENERATED ALWAYS AS (data->>'code') VIRTUAL,
    device_id TEXT GENERATED ALWAYS AS (data->>'device_id') VIRTUAL,
    endpoint TEXT GENERATED ALWAYS AS (data->>'endpoint') VIRTUAL
);
CREATE UNIQUE INDEX IF NOT EXISTS push_subs_code_endpoint ON push_subs (code, endpoint);
"""


def schema(tx: Tx) -> None:
    tx.execute(SCHEMA)


def add_sub(tx: Tx, code: str, device_id: str, sub: dict, kinds: list[str]) -> None:
    tx.execute(
        "INSERT INTO push_subs (id, data) VALUES (:id, :data)"
        " ON CONFLICT (code, endpoint) DO UPDATE SET data = excluded.data",
        id=f"{code}:{sub['endpoint']}",
        data=json.dumps(
            {
                "code": code,
                "device_id": device_id,
                "endpoint": sub["endpoint"],
                "p256dh": sub["keys"]["p256dh"],
                "auth": sub["keys"]["auth"],
                "kinds": kinds,
                "created_at": time.time(),
            }
        ),
    )


def subs_for(db, code: str) -> list[dict]:
    return db.query(
        "SELECT data->>'device_id' AS device_id, data->>'endpoint' AS endpoint,"
        " data->>'p256dh' AS p256dh, data->>'auth' AS auth,"
        " data->>'kinds' AS kinds FROM push_subs WHERE code = :code",
        code=code,
    )


def set_kinds(tx: Tx, code: str, device_id: str, kinds: list[str]) -> None:
    tx.execute(
        "UPDATE push_subs SET data = json_set(data, '$.kinds', json(:kinds))"
        " WHERE code = :code AND device_id = :did",
        code=code,
        did=device_id,
        kinds=json.dumps(kinds),
    )


def delete_of(tx: Tx, code: str, device_id: str) -> None:
    tx.execute(
        "DELETE FROM push_subs WHERE code = :code AND device_id = :did",
        code=code,
        did=device_id,
    )


def delete_endpoint(tx: Tx, code: str, endpoint: str) -> None:
    tx.execute(
        "DELETE FROM push_subs WHERE code = :code AND endpoint = :ep",
        code=code,
        ep=endpoint,
    )


def delete_room(tx: Tx, code: str) -> None:
    tx.execute("DELETE FROM push_subs WHERE code = :code", code=code)
