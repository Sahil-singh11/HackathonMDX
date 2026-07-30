"""Task 4b — Marine Transport & Trade pillar.

Covers the promises the pillar makes, in the order they matter:

1. The model cannot invent a vessel. Counts, ETAs and ordering are computed
   from AIS fields; a narrative citing an unknown identifier is rejected.
2. Provenance is honest — `data_kind` is `synthetic` while the data is
   synthetic, and both coverage sentences are present verbatim.
3. The rolling store stays bounded by both the time window and the row cap.
4. Enable/disable, throttling and demo-reset behave as the contract says.
5. Zero network: every test here runs under the autouse socket guard.

The default suite never touches a provider — `PROVIDER_MODE=mock` is set in
conftest, and a simulated provider deliberately routes to the deterministic
narrative. The model path is exercised with stub providers instead, which is
what "model mocked in the default suite" has to mean for a pillar whose whole
design is that the model never produces data.

`fetch`/`analyse` are async by contract, driven here with `asyncio.run` rather
than a plugin: the suite has no async runner installed and adding one for four
call sites is not worth a dependency announcement.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.session import get_engine
from app.inference.base import ProviderHealth
from app.models.entities import AisPosition
from app.pillars.transport import ais, brief, store
from app.pillars.transport.module import COVERAGE_NOTE, transport_pillar

SYNTHETIC_MMSIS = {645123456, 645234567, 645345678, 645456789, 645567890, 645678901,
                   645789012, 645890123, 645901234, 646012345, 646123450, 646234561}


@pytest.fixture
def session():
    with Session(get_engine()) as s:
        yield s


@pytest.fixture
def enabled(monkeypatch):
    """Enable the pillar for one test without changing the shipped default."""
    monkeypatch.setenv("PILLARS_ENABLED", "fisheries,transport")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _brief(session, **params):
    async def go():
        bundle = await transport_pillar.fetch({"session": session, **params})
        return await transport_pillar.analyse(bundle)

    return asyncio.run(go())


def _stub(name: str, reply=None, *, raises: Exception | None = None,
          simulated: bool = False, available: bool = True):
    class StubProvider:
        def __init__(self) -> None:
            self.name = name
            self.seen_prompt = ""
            self.seen_instruction = None
            self.seen_timeout = None

        def chat(self, prompt, language="en", system_instruction=None,
                 timeout_seconds=None):
            self.seen_prompt = prompt
            self.seen_instruction = system_instruction
            self.seen_timeout = timeout_seconds
            if raises is not None:
                raise raises
            return reply

        def health_check(self):
            return ProviderHealth(name=name, available=available, real_inference=not simulated,
                                  simulated=simulated, detail="stub")

    return StubProvider()


def _use(monkeypatch, provider):
    monkeypatch.setattr("app.pillars.transport.module.select_provider",
                        lambda *a, **k: (provider, []))
    return provider


# -- 1. the model cannot invent data -----------------------------------------

def test_every_vessel_in_the_brief_came_from_the_ais_data(session):
    result = _brief(session)
    assert result.expected_arrivals_count >= 1
    for arrival in result.expected_arrivals:
        assert arrival.mmsi in SYNTHETIC_MMSIS


def test_arrivals_are_filtered_and_ordered_deterministically(session):
    first = _brief(session)
    second = _brief(session)
    assert [a.mmsi for a in first.expected_arrivals] == [a.mmsi for a in second.expected_arrivals]
    etas = [a.reported_eta_utc for a in first.expected_arrivals]
    assert etas == sorted(etas), "ordering comes from the ETA field, never the model"
    for a in first.expected_arrivals:
        assert 0 <= a.hours_to_reported_eta <= first.window_hours


def test_outbound_and_out_of_window_vessels_are_excluded(session):
    ids = {a.mmsi for a in _brief(session).expected_arrivals}
    assert 645901234 not in ids, "PETREL EXPRESS reports PORT REUNION — not an arrival here"
    assert 646234561 not in ids, "GRAND BAIE PIONEER's reported ETA is beyond the 24 h window"
    assert 645678901 not in ids, "KAI XIN's reported ETA is in the past"
    assert 645567890 not in ids, "LADY SUSHIL sends the AIS 'ETA not available' sentinel"


def test_vessels_without_identity_are_counted_but_never_named(session):
    result = _brief(session)
    assert result.congestion.identity_unknown == 2
    for arrival in result.expected_arrivals:
        if not arrival.identity_known:
            assert arrival.vessel_name is None


def test_narrative_grounding_rejects_an_invented_identifier():
    known = {645123456}
    ok, _ = brief.narrative_is_grounded("MSC LORETO is inbound, reported ETA 10:00.", known)
    assert ok
    bad, reason = brief.narrative_is_grounded("Vessel 999888777 is also inbound.", known)
    assert not bad and "999888777" in reason


def test_narrative_grounding_rejects_empty_output():
    ok, reason = brief.narrative_is_grounded("   ", {645123456})
    assert not ok and "empty" in reason


def test_narrative_grounding_rejects_the_assistant_envelope():
    """Regression: this is the REAL hosted-Gemma output captured on 30 Jul 2026.

    chat() injects the fisheries SYSTEM_INSTRUCTION, so the live model refused
    the port task and wrapped the refusal in the catch-assistant JSON envelope.
    An earlier version of this guard passed it through as narrative_source
    'model' — a refusal presented to a port officer as a brief.
    """
    captured = (
        '```json\n{\n  "intent": "other",\n'
        '  "reply": "I am an analysis engine for fishers, not a port officer. '
        'I cannot write reports for maritime authorities.",\n'
        '  "reply_morisyen": "Mo enn analiz pou peser, pa enn ofiser port.",\n'
        '  "call": null\n}\n```'
    )
    ok, reason = brief.narrative_is_grounded(captured, {645123456})
    assert not ok
    assert "structured output" in reason


def test_narrative_grounding_rejects_bare_json_and_envelope_keys():
    ok, reason = brief.narrative_is_grounded('{"intent": "other"}', {645123456})
    assert not ok and "structured output" in reason
    ok, reason = brief.narrative_is_grounded(
        'intent: "intent" and "reply_morisyen" were requested', {645123456})
    assert not ok and "structured envelope" in reason


def test_narrative_grounding_still_accepts_ordinary_prose():
    ok, _ = brief.narrative_is_grounded(
        "Five vessels report Port Louis. Swell is moderate and berthing should hold.",
        {645123456})
    assert ok


def test_ungrounded_model_output_falls_back_and_says_why(session, monkeypatch):
    _use(monkeypatch, _stub("stub_hallucinating",
                            "Vessel 111222333 is inbound.\n\nSeas are calm."))
    result = _brief(session)
    assert result.narrative_source == "deterministic_fallback"
    assert "111222333" in result.narrative_note
    assert "111222333" not in result.narrative


def test_grounded_model_output_is_used_and_labelled(session, monkeypatch):
    provider = _use(monkeypatch, _stub(
        "stub_good", "Five vessels report Port Louis.\n\nSwell is moderate; berthing should hold."))
    result = _brief(session)
    assert result.narrative_source == "model"
    assert result.narrative.startswith("Five vessels")
    assert "berthing" in result.risk_reasoning
    assert result.provenance.model_provider == "stub_good"
    # The honesty rules live in the transport-scoped system instruction
    # (decision log 17), not the fisheries default the provider would otherwise use.
    assert provider.seen_instruction is brief.SYSTEM_INSTRUCTION
    assert "Never invent a vessel" in provider.seen_instruction
    assert "Never state an MMSI" in provider.seen_instruction
    assert "maritime operations analyst" in provider.seen_instruction
    # Route-local timeout (decision log 18). The route carries its own ceiling
    # explicitly even though it currently equals the global default: 90 s was
    # tried, timed out anyway, and was reverted as net-harmful. Asserting the
    # wiring rather than a magic number keeps that knob honest.
    assert provider.seen_timeout == get_settings().transport_narrative_timeout_seconds
    assert "Do NOT invent a vessel" in provider.seen_prompt


def test_single_paragraph_reply_does_not_get_split_into_fake_structure(session, monkeypatch):
    _use(monkeypatch, _stub("stub_terse", "Traffic is light and the approach is clear."))
    result = _brief(session)
    assert result.narrative_source == "model"
    assert result.narrative == "Traffic is light and the approach is clear."
    assert "single paragraph" in result.narrative_note
    assert "No model reasoned over these figures" in result.risk_reasoning


def test_provider_failure_degrades_instead_of_raising(session, monkeypatch):
    _use(monkeypatch, _stub("stub_broken", raises=RuntimeError("upstream exploded")))
    result = _brief(session)
    assert result.narrative_source == "deterministic_fallback"
    assert "upstream exploded" in result.narrative_note


def test_unavailable_provider_degrades_and_says_so(session, monkeypatch):
    _use(monkeypatch, _stub("stub_down", "unused", available=False))
    result = _brief(session)
    assert result.narrative_source == "deterministic_fallback"
    assert "provider unavailable" in result.narrative_note


def test_mock_provider_does_not_pretend_to_have_reasoned(session):
    """conftest forces PROVIDER_MODE=mock, so this is the default-suite path."""
    result = _brief(session)
    assert result.narrative_source == "deterministic_fallback"
    assert "disclosed mock" in result.narrative_note
    assert "No model reasoned over these figures" in result.narrative


# -- 2. provenance -----------------------------------------------------------

def test_synthetic_data_is_labelled_synthetic_not_sample(session):
    result = _brief(session)
    assert result.provenance.data_kind == "synthetic", (
        "'sample' means a real capture; this is constructed from the schema"
    )
    assert result.provenance.source_name == "aisstream.io"


def test_coverage_note_carries_both_honesty_statements(session):
    note = _brief(session).provenance.coverage_note
    assert note == COVERAGE_NOTE
    assert "self-reported by vessels over AIS" in note
    assert "not port authority data" in note
    assert "nearshore and incomplete" in note


def test_coverage_note_states_why_the_data_is_synthetic(session):
    """The probe finding travels with every response, not just the PR."""
    note = _brief(session).provenance.coverage_note
    assert "probed on 30 Jul 2026" in note
    assert "zero messages for the Mauritius region" in note
    assert "until a covered feed exists" in note


def test_scope_note_disclaims_model_authorship_of_data(session):
    result = _brief(session)
    assert result.advisory is True
    assert "No vessel, MMSI or timestamp in this response was produced by a model" in result.scope_note


def test_retrieved_at_is_timezone_aware(session):
    assert _brief(session).provenance.retrieved_at.tzinfo is not None


# -- 3. the store stays bounded ----------------------------------------------

def test_prune_drops_rows_outside_the_retention_window(session, monkeypatch):
    monkeypatch.setattr(get_settings(), "transport_ais_retention_minutes", 60)
    now = _now()
    session.add(AisPosition(mmsi=1, received_at=now - timedelta(minutes=5),
                            time_utc=now, latitude=-20.1, longitude=57.5))
    session.add(AisPosition(mmsi=2, received_at=now - timedelta(minutes=600),
                            time_utc=now, latitude=-20.1, longitude=57.5))
    session.commit()
    store.prune(session, now=now)
    session.commit()
    kept = {r.mmsi for r in session.exec(select(AisPosition)).all()}
    assert 1 in kept and 2 not in kept


def test_prune_enforces_the_row_cap_keeping_the_newest(session, monkeypatch):
    monkeypatch.setattr(get_settings(), "transport_ais_max_rows", 5)
    now = _now()
    for i in range(20):
        session.add(AisPosition(mmsi=1000 + i, received_at=now - timedelta(seconds=20 - i),
                                time_utc=now, latitude=-20.1, longitude=57.5))
    session.commit()
    store.prune(session, now=now)
    session.commit()
    rows = session.exec(select(AisPosition)).all()
    assert len(rows) == 5
    assert {r.mmsi for r in rows} == {1015, 1016, 1017, 1018, 1019}


def test_recording_prunes_in_the_same_call(session, monkeypatch):
    monkeypatch.setattr(get_settings(), "transport_ais_max_rows", 3)
    now = _now()
    obs = [ais.AisObservation(mmsi=2000 + i, latitude=-20.1, longitude=57.5, time_utc=now)
           for i in range(10)]
    store.record(session, obs, "synthetic", now=now)
    assert len(session.exec(select(AisPosition)).all()) == 3


def test_reads_never_return_rows_older_than_the_window(session, monkeypatch):
    monkeypatch.setattr(get_settings(), "transport_ais_retention_minutes", 30)
    now = _now()
    session.add(AisPosition(mmsi=77, received_at=now - timedelta(hours=5),
                            time_utc=now, latitude=-20.1, longitude=57.5))
    session.commit()
    assert 77 not in {r.mmsi for r in store.latest_per_vessel(session, now=now)}


# -- 4. AIS parsing edge cases -----------------------------------------------

def test_position_without_static_data_keeps_the_vessel_but_not_an_identity():
    msgs = [{
        "MessageType": "PositionReport",
        "MetaData": {"MMSI": 123456789, "ShipName": "", "latitude": -20.2, "longitude": 57.4,
                     "time_utc": "2026-07-30 07:00:00.000000000 +0000 UTC"},
        "Message": {"PositionReport": {"Latitude": -20.2, "Longitude": 57.4,
                                       "NavigationalStatus": 0, "Sog": 8.0, "Cog": 45.0}},
    }]
    obs = ais.normalise(msgs, _now())
    assert len(obs) == 1
    assert obs[0].ship_name is None and obs[0].destination is None and obs[0].eta_utc is None
    assert obs[0].ship_type_label == "unknown"


def test_static_data_alone_does_not_create_a_vessel():
    """Identity with no position is not an observation — we cannot place it."""
    msgs = [{
        "MessageType": "ShipStaticData",
        "MetaData": {"MMSI": 111111111, "ShipName": "GHOST",
                     "time_utc": "2026-07-30 07:00:00.000000000 +0000 UTC"},
        "Message": {"ShipStaticData": {"Name": "GHOST", "Destination": "PORT LOUIS", "Type": 70}},
    }]
    assert ais.normalise(msgs, _now()) == []


def test_eta_sentinel_resolves_to_none():
    assert ais.resolve_eta({"Month": 0, "Day": 0, "Hour": 24, "Minute": 60}, _now()) is None
    assert ais.resolve_eta(None, _now()) is None


def test_eta_year_is_inferred_as_the_nearest_occurrence():
    reference = datetime(2027, 1, 1, 6, 0, tzinfo=timezone.utc)
    eta = ais.resolve_eta({"Month": 12, "Day": 31, "Hour": 22, "Minute": 0}, reference)
    assert eta is not None and eta.year == 2026, "a 31 Dec ETA read on 1 Jan is yesterday"


def test_go_timestamp_with_nanoseconds_parses():
    parsed = ais.parse_time_utc("2026-07-30 07:59:12.418000000 +0000 UTC")
    assert parsed is not None and parsed.tzinfo is not None
    assert (parsed.year, parsed.month, parsed.day, parsed.hour) == (2026, 7, 30, 7)


def test_synthetic_file_is_rebased_onto_the_reference_clock():
    path = get_settings().data_dir / "pillars" / "transport" / "ais_synthetic_port_louis.json"
    reference = _now()
    messages, declared = ais.load_synthetic(path, reference)
    stamps = [s for s in (ais.parse_time_utc(m["MetaData"]["time_utc"]) for m in messages) if s]
    assert abs((max(stamps) - reference).total_seconds()) < 1, "newest message lands on 'now'"
    assert min(stamps) < max(stamps), "relative spacing is preserved, not flattened"
    assert declared.year == 2026, "the file's own declared reference instant survives"


def test_destination_matching_is_tolerant_but_not_greedy():
    assert brief.is_bound_for_port_louis("PORT LOUIS")
    assert brief.is_bound_for_port_louis("portlouis")
    assert brief.is_bound_for_port_louis("MUPLU")
    assert not brief.is_bound_for_port_louis("PORT REUNION")
    assert not brief.is_bound_for_port_louis("")
    assert not brief.is_bound_for_port_louis(None)


# -- 5. route behaviour ------------------------------------------------------

def test_arrivals_route_is_503_while_the_pillar_is_disabled(client):
    """The shipped default is implemented but NOT enabled."""
    assert client.get("/api/pillars/transport/arrivals").status_code == 503


def test_arrivals_route_serves_when_enabled(client, enabled):
    r = client.get("/api/pillars/transport/arrivals")
    assert r.status_code == 200
    body = r.json()
    assert body["pillar_id"] == "transport"
    assert body["provenance"]["data_kind"] == "synthetic"
    assert body["provenance"]["coverage_note"] == COVERAGE_NOTE
    assert body["expected_arrivals_count"] == len(body["expected_arrivals"])
    assert body["narrative_source"] in {"model", "deterministic_fallback"}


def test_provenance_route_is_503_while_the_pillar_is_disabled(client):
    assert client.get("/api/pillars/transport/provenance").status_code == 503


def test_provenance_probe_is_cheap_and_never_claims_inference(client, enabled):
    """Same convention as tourism/energy (test_pillar_probe.py): fetch() only,
    no narrative call. Fills a gap the /pillars index previously rendered as
    "not reported" for transport specifically."""
    import time

    from app.pillars.probe import NOT_INVOKED

    start = time.monotonic()
    r = client.get("/api/pillars/transport/provenance")
    elapsed = time.monotonic() - start

    assert r.status_code == 200
    body = r.json()
    assert body["pillar_id"] == "transport"
    assert body["probe"] is True
    assert body["provenance"]["data_kind"] == "synthetic"
    assert body["provenance"]["model_provider"] == NOT_INVOKED
    assert elapsed < 5.0, f"probe took {elapsed:.2f}s — has a model call crept in?"


def test_listing_reports_transport_as_implemented(client):
    body = client.get("/api/pillars").json()
    transport = {p["pillar_id"]: p for p in body["pillars"]}["transport"]
    assert transport["implemented"] is True
    assert transport["enabled"] is False
    assert "/api/pillars/transport/arrivals" in transport["endpoints"]


def test_arrivals_route_is_openapi_documented(client):
    spec = client.get("/openapi.json").json()
    path = spec["paths"]["/api/pillars/transport/arrivals"]["get"]
    assert "self-reported" in path["description"]
    assert "nearshore and incomplete" in path["description"]


def test_demo_reset_clears_stored_positions(client, session):
    now = _now()
    session.add(AisPosition(mmsi=999, received_at=now, time_utc=now,
                            latitude=-20.1, longitude=57.5))
    session.commit()
    assert session.exec(select(AisPosition)).all()
    client.post("/api/demo/reset")
    session.expire_all()
    assert not session.exec(select(AisPosition)).all()


# -- 6. no network -----------------------------------------------------------

def test_brief_builds_with_zero_network(session):
    """The autouse socket guard is active; marine data degrades to its
    deterministic mock and the brief is still produced."""
    result = _brief(session)
    assert result.expected_arrivals_count >= 1
    assert result.conditions.get("wave_height_m") is not None


def test_collector_is_disabled_by_default():
    """The live collector is deliberately unimplemented — the 30 Jul coverage
    probe found no AIS receiver traffic for the region — so these settings are
    dormant forward declarations and must stay off until that changes."""
    settings = get_settings()
    assert settings.ais_collector_enabled is False
    assert settings.aisstream_api_key == ""
