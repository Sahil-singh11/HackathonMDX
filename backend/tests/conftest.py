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
os.environ["GEMINI_API_KEY"] = ""
os.environ["MARINE_PREWARM_ON_STARTUP"] = "false"  # suite must not depend on live network


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
