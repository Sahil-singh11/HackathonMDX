"""SPA deep-link fallback.

The frontend is a client-side router served by StaticFiles. Without a fallback,
StaticFiles raises 404 for any path deeper than "/", so opening /sea,
/authority or /verify/<id> directly returned {"detail":"Not Found"}.

That is fatal for /verify/<id> specifically: it is the QR-code landing page for
a certificate, so a buyer or inspector arrives there by deep link every single
time, never by in-app navigation. The bug was masked in a browser because the
service worker served a cached index.html once the PWA had been visited.

These tests also pin the two things the fallback must NOT do: swallow missing
assets, and swallow unmatched API routes.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

pytestmark = pytest.mark.skipif(
    not DIST.exists(), reason="frontend/dist not built; SPA mount is not registered"
)

# NOTE: `client` is the session fixture from conftest.py. Do not define a local
# one - it shadows the shared fixture, skips the isolated test-database setup,
# and makes this module pass only when run after the rest of the suite.


@pytest.mark.parametrize("path", [
    "/", "/sea", "/record", "/log", "/declaration", "/queue", "/proof",
    "/demo", "/privacy", "/about", "/authority", "/verify/abc123",
    # Legacy paths kept alive for existing links/QR codes.
    "/marine", "/catch", "/history",
])
def test_client_routes_serve_the_app_shell(client: TestClient, path: str) -> None:
    res = client.get(path)
    assert res.status_code == 200, f"{path} should fall back to index.html"
    assert "text/html" in res.headers["content-type"]


@pytest.mark.parametrize("path", ["/nope.js", "/missing.png", "/assets/gone.css"])
def test_missing_assets_still_404(client: TestClient, path: str) -> None:
    """A broken script or image must not be disguised as the app shell, or
    debugging a bad build becomes guesswork."""
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/api/does-not-exist", "/api/catches/nope/nope"])
def test_unknown_api_routes_still_404(client: TestClient, path: str) -> None:
    """An unmatched API route must return JSON 404, not HTML.

    Regression guard: the first implementation checked `path.startswith("api/")`,
    but StaticFiles hands over OS-native separators, so on Windows the value is
    "api\\does-not-exist" and the check silently passed the request through to
    index.html. It only behaved correctly on Linux.
    """
    res = client.get(path)
    assert res.status_code == 404
    assert "text/html" not in res.headers.get("content-type", "")


def test_real_api_routes_are_unaffected(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/api/config/public").status_code == 200
