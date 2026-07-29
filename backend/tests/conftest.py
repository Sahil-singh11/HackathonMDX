import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Isolated test database + forced mock provider before app import.
_TEST_DB = BACKEND.parent / "storage" / "test_lamer.sqlite3"
_TEST_DB.parent.mkdir(parents=True, exist_ok=True)
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["PROVIDER_MODE"] = "mock"
# Preserve an exported key for the live tier BEFORE blanking it for the app
# under test. Live tests read GEMINI_API_KEY_LIVE only — never .env — so the
# default suite cannot pick up a key by accident.
os.environ.setdefault("GEMINI_API_KEY_LIVE", os.environ.get("GEMINI_API_KEY", ""))
os.environ["GEMINI_API_KEY"] = ""
os.environ["MARINE_PREWARM_ON_STARTUP"] = "false"  # suite must not depend on live network


@pytest.fixture(autouse=True)
def _no_external_network(request, monkeypatch):
    """Socket guard: the default suite makes ZERO external network calls.

    Any attempt to resolve or connect to a non-local host raises. Code built
    for the sea degrades gracefully (the marine client falls back to cache or
    its deterministic mock on connection errors), so this both proves the
    no-network property and continuously exercises offline behaviour.
    Live-marked tests are exempt — they exist to hit the real API.
    """
    if request.node.get_closest_marker("live"):
        yield
        return

    import socket as _socket

    _LOCAL = {"localhost", "127.0.0.1", "::1", "testserver", ""}
    real_getaddrinfo = _socket.getaddrinfo
    real_connect = _socket.socket.connect

    def guarded_getaddrinfo(host, *args, **kwargs):
        if str(host) in _LOCAL:
            return real_getaddrinfo(host, *args, **kwargs)
        raise _socket.gaierror(f"[socket guard] external DNS blocked in default suite: {host!r}")

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if str(host) in _LOCAL or str(host).startswith(("127.", "::1")):
            return real_connect(self, address)
        raise OSError(f"[socket guard] external connect blocked in default suite: {host!r}")

    monkeypatch.setattr(_socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(_socket.socket, "connect", guarded_connect)
    yield


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_demo_state(client):
    yield
    client.post("/api/demo/reset")


@pytest.fixture
def sharp_image() -> bytes:
    root = BACKEND.parent
    p = root / "data" / "demo" / "synthetic" / "sharp.jpg"
    return p.read_bytes()


@pytest.fixture
def blurry_image() -> bytes:
    root = BACKEND.parent
    return (root / "data" / "demo" / "synthetic" / "blurry.jpg").read_bytes()
