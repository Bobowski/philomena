"""The push adapter: one sync send; tests replace the class with a fake."""

import json
from typing import Any

from pywebpush import WebPusher


class PushSender:
    def __init__(self, pem_path: str, sub_claim: str) -> None:
        self.pem_path = pem_path
        self.claims = {"sub": sub_claim}

    def send(self, sub: dict, payload: dict) -> int:
        resp: Any = WebPusher(sub).send(
            data=json.dumps(payload),
            vapid_private_key=self.pem_path,
            vapid_claims=self.claims,
        )
        return int(resp.status_code)
