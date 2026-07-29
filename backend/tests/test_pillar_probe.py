"""Provenance probe convention (Task 5d).

The probe exists so the /pillars index can show data_kind without paying for a
full result. What must hold:
  * it reports the REAL data_kind, source and coverage note
  * it never claims a model served the request, because none did
  * a pillar that has not adopted the convention 404s, so the UI shows an
    absence rather than a guessed label
"""
from __future__ import annotations

import asyncio

from app.pillars.energy.module import energy_pillar
from app.pillars.probe import NOT_INVOKED, probe_provenance
from app.pillars.tourism.module import tourism_pillar


def _probe(pillar):
    from sqlmodel import Session

    from app.db.session import get_engine
    with Session(get_engine()) as session:
        return asyncio.run(probe_provenance(
            pillar, {"session": session, "allow_network": False}))


def test_probe_reports_real_data_kind_and_source(client):
    for pillar in (tourism_pillar, energy_pillar):
        body = _probe(pillar)
        assert body["pillar_id"] == pillar.pillar_id
        assert body["probe"] is True
        assert body["provenance"]["data_kind"] in ("live", "cached", "sample", "synthetic")
        assert body["provenance"]["source_name"]
        assert body["provenance"]["coverage_note"]


def test_probe_never_claims_a_model_served_the_request(client):
    """No inference runs in a probe, so naming a provider would be a false claim."""
    body = _probe(tourism_pillar)
    assert body["provenance"]["model_provider"] == NOT_INVOKED
    # The provider that WOULD serve is reported separately — a different claim.
    assert body["would_use_provider"]
    assert body["would_use_provider"] != NOT_INVOKED


def test_probe_explains_what_it_did_not_do(client):
    note = _probe(energy_pillar)["note"].lower()
    assert "no model inference" in note or "no model" in note


def test_probe_offline_is_never_labelled_live(client):
    body = _probe(energy_pillar)
    assert body["provenance"]["data_kind"] != "live"


def test_probe_routes_are_gated_like_every_other_pillar_route(client):
    """Default PILLARS_ENABLED is "fisheries", so both probes must 503."""
    for pillar_id in ("tourism", "energy"):
        assert client.get(f"/api/pillars/{pillar_id}/provenance").status_code == 503


def test_a_pillar_without_the_convention_404s_rather_than_inventing_one(client):
    """fisheries is live but served by the production routes, not a pillar module,
    so it has no /provenance. The index must render that absence."""
    r = client.get("/api/pillars/fisheries/provenance")
    assert r.status_code in (404, 503), r.status_code
    assert "data_kind" not in r.text


def test_probe_is_cheap_enough_for_an_index_page(client):
    """Guards the whole point of the probe: a full result costs model calls
    (measured >120 s), so this path must not acquire one."""
    import time
    start = time.monotonic()
    _probe(tourism_pillar)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"probe took {elapsed:.2f}s — has a model call crept in?"
