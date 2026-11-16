import os
from dataclasses import dataclass
from pathlib import Path

from app.assets import OG_IMAGE


def _csv(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(s for s in (p.strip() for p in os.environ.get(name, default).split(",")) if s)


@dataclass(frozen=True, slots=True)
class Config:
    app_name: str
    data_dir: Path
    stun_urls: tuple[str, ...]
    turn_urls: tuple[str, ...]
    turn_secret: str
    turn_ttl: int
    public_url: str
    offline_push_after: float = 60.0

    @property
    def db_path(self) -> Path:
        return self.data_dir / "philomena.sqlite3"

    @property
    def og_image(self) -> str:
        return self.public_url.rstrip("/") + OG_IMAGE

    @classmethod
    def from_env(cls) -> Config:
        data_dir = Path(os.environ.get("PROJECT_DATA_DIR", "data"))
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            app_name=os.environ.get("APP_NAME", "philomena"),
            data_dir=data_dir,
            stun_urls=_csv("STUN_URLS", "stun:stun.l.google.com:19302"),
            turn_urls=_csv("TURN_URLS"),
            # COTURN_STATIC_AUTH_SECRET is the key the old deployment already sets.
            turn_secret=os.environ.get("COTURN_STATIC_AUTH_SECRET", ""),
            turn_ttl=int(os.environ.get("TURN_TTL", "86400")),
            # the HTTPS address of this install; previews and Web Push need it
            public_url=os.environ.get("PUBLIC_URL", "http://localhost:8000"),
            offline_push_after=float(os.environ.get("OFFLINE_PUSH_AFTER", "60")),
        )
