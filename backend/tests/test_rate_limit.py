"""Per-IP throttle on /api/analyse-catch (in-memory, ~10/min)."""
from app.core.ratelimit import InMemoryRateLimiter


def test_analyse_catch_throttled_after_ten_per_minute(client):
    for i in range(10):
        r = client.post("/api/analyse-catch", data={"note": f"test {i}", "provider_mode": "mock"})
        assert r.status_code == 200, r.text
    r = client.post("/api/analyse-catch", data={"note": "eleventh", "provider_mode": "mock"})
    assert r.status_code == 429
    assert "Too many" in r.json()["detail"]


def test_demo_reset_clears_the_throttle(client):
    for i in range(10):
        client.post("/api/analyse-catch", data={"note": f"test {i}", "provider_mode": "mock"})
    assert client.post("/api/analyse-catch", data={"note": "over", "provider_mode": "mock"}).status_code == 429

    client.post("/api/demo/reset")

    r = client.post("/api/analyse-catch", data={"note": "fresh after reset", "provider_mode": "mock"})
    assert r.status_code == 200


def test_limiter_is_per_key_and_resettable():
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False  # "a" exhausted
    assert limiter.allow("b") is True   # "b" unaffected by "a"'s usage

    limiter.reset()
    assert limiter.allow("a") is True  # cleared
