"""Startup marine-cache pre-warm: must call every demo location and must
never let one failure block the others (no live network in this test)."""
from app.services.marine import client as marine_client


def test_prewarm_calls_every_demo_location(monkeypatch):
    calls = []
    monkeypatch.setattr(marine_client, "get_marine_conditions",
                        lambda session, lat, lon: calls.append((lat, lon)) or {"source": "open-meteo"})
    marine_client.prewarm_demo_locations(session=None)
    assert calls == [(lat, lon) for _name, lat, lon in marine_client.DEMO_LOCATIONS]


def test_prewarm_survives_one_location_failing(monkeypatch):
    calls = []

    def flaky(session, lat, lon):
        if len(calls) == 1:  # fail on the second location only
            calls.append((lat, lon))
            raise RuntimeError("simulated network failure")
        calls.append((lat, lon))
        return {"source": "open-meteo"}

    monkeypatch.setattr(marine_client, "get_marine_conditions", flaky)
    marine_client.prewarm_demo_locations(session=None)  # must not raise
    assert len(calls) == 3  # all three still attempted despite the middle one failing
