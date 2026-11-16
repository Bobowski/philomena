import pytest
from stario.testing import TestClient

from app.main import bootstrap


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OFFLINE_PUSH_AFTER", "0.1")
    # `just` loads .env; a real TURN secret must not leak into the STUN-only tests.
    monkeypatch.delenv("TURN_URLS", raising=False)
    monkeypatch.delenv("COTURN_STATIC_AUTH_SECRET", raising=False)
    async with TestClient(bootstrap, request_timeout=5) as c:
        yield c


@pytest.fixture
async def turn_client(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OFFLINE_PUSH_AFTER", "0.1")
    monkeypatch.setenv("TURN_URLS", "turn:turn.example.com:3478")
    monkeypatch.setenv("COTURN_STATIC_AUTH_SECRET", "test-secret")
    async with TestClient(bootstrap, request_timeout=5) as c:
        yield c
