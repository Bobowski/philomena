"""ICE server list with fresh TURN credentials for each stream connect."""

import base64
import hashlib
import hmac
import secrets
import time

from app.config import Config


def turn_credentials(secret: str, ttl: int) -> tuple[str, str]:
    username = f"{int(time.time()) + ttl}:{secrets.token_hex(16)}"
    key = hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()
    return username, base64.b64encode(key).decode()


def ice_servers(config: Config) -> list[dict[str, object]]:
    servers: list[dict[str, object]] = [{"urls": list(config.stun_urls)}]
    if config.turn_urls and config.turn_secret:
        username, credential = turn_credentials(config.turn_secret, config.turn_ttl)
        servers.append(
            {
                "urls": list(config.turn_urls),
                "username": username,
                "credential": credential,
            }
        )
    return servers
