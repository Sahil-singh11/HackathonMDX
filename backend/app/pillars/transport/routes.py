"""Transport pillar routes, mounted at /api/pillars/transport/.

The enabled-check (503 while disabled) and the per-IP throttle are applied by
`PillarRegistry.mount_all`, not here — this router declares only what is
specific to the pillar.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.pillars.probe import probe_provenance
from app.pillars.transport.module import (COVERAGE_NOTE, ArrivalsBrief,
                                          transport_pillar)

router = APIRouter()

# A REAL captured response from a LIVE hosted-Gemma call, trimmed to two
# arrivals. Re-captured 30 Jul 2026 22:51 UTC after the system-instruction change
# (decision log 17), so it reflects the current code path. Nothing here was
# written by hand to look good — an example that does not match what the endpoint
# returns is worse than none.
#
# Read the two provenance fields together, because their split is the point:
#   data_kind      "synthetic"    <- where the VESSEL DATA came from
#   model_provider "gemma_hosted" <- which model served the NARRATIVE step
# A real model reasoning over honestly-labelled synthetic data is not the same
# claim as live data, and the payload keeps the two separable.
#
# `narrative_source` is `deterministic_fallback` because THIS capture hit the
# 60 s hosted timeout (`GEMMA_TIMEOUT_SECONDS`) — a transport-layer outage, not a
# refusal. The degradation path did exactly its job and recorded the real reason.
#
# History worth keeping straight: an earlier capture failed differently. Under the
# fisheries default instruction the model REFUSED the port task and answered with
# the catch-assistant JSON envelope; that is what motivated decision log 17 and it
# is pinned in
# tests/test_pillar_transport.py::test_narrative_grounding_rejects_the_assistant_envelope.
# That failure mode is fixed. This one is a timeout, and no grounded-prose capture
# has been obtained yet — the two authorised live calls after the fix hit a
# transient Google 503 and this timeout. Stated rather than papered over: we do
# not yet have a measured example of real Gemma prose in this field.
ARRIVALS_EXAMPLE = {
    "pillar_id": "transport",
    "generated_at": "2026-07-29T22:51:55.024792Z",
    "provenance": {
        "source_name": "aisstream.io",
        "source_url": "https://aisstream.io",
        "retrieved_at": "2026-07-29T22:51:55.024792Z",
        "data_kind": "synthetic",
        "model_provider": "gemma_hosted",
        "coverage_note": COVERAGE_NOTE,
    },
    "port": {"name": "Port Louis", "unlocode": "MUPLU", "latitude": -20.158, "longitude": 57.488},
    "window_hours": 24,
    "expected_arrivals": [
        {
            "mmsi": 645123456, "vessel_name": "MSC LORETO", "identity_known": True,
            "vessel_type": "cargo", "nav_status": "under way using engine",
            "destination_reported": "PORT LOUIS",
            "reported_eta_utc": "2026-07-30T10:00:00+00:00", "hours_to_reported_eta": 11.1,
            "distance_nm": 6.36, "speed_knots": 11.4, "draught_m": 11.2,
            "last_seen_utc": "2026-07-29T22:51:55.024792+00:00",
        },
        {
            "mmsi": 645234567, "vessel_name": "CMA CGM MASCAREIGNE", "identity_known": True,
            "vessel_type": "cargo", "nav_status": "under way using engine",
            "destination_reported": "PORT LOUIS",
            "reported_eta_utc": "2026-07-30T14:30:00+00:00", "hours_to_reported_eta": 15.6,
            "distance_nm": 10.66, "speed_knots": 14.1, "draught_m": 12.8,
            "last_seen_utc": "2026-07-29T22:50:38.476792+00:00",
        },
    ],
    "expected_arrivals_count": 5,
    "congestion": {
        "vessels_tracked": 12, "under_way": 9, "at_anchor": 2, "moored": 1,
        "other_or_unknown_status": 0, "within_approach_radius": 8,
        "approach_radius_nm": 10.0, "identity_unknown": 2,
        "note": ("Counts are every vessel in the retention window, tallied by AIS navigational "
                 "status. 'identity_unknown' vessels sent a position but no static data, so "
                 "their name, type, destination and ETA are genuinely unknown \u2014 they are "
                 "counted, never named or guessed."),
    },
    "conditions": {
        "location": "-20.16,57.49", "source": "open-meteo", "mock": False,
        "wave_height_m": 1.46, "swell_height_m": 1.36, "swell_period_s": 10.4,
        "sea_surface_temperature_c": 25.1,
    },
    "narrative": (
        "5 vessel(s) report Port Louis as their destination within the next 24 hours; the "
        "earliest is MSC LORETO, reported ETA 2026-07-30T10:00:00+00:00. 12 vessel(s) are "
        "tracked in the window: 9 under way, 2 at anchor, 1 moored, 2 without identifying "
        "static data. Reported sea state at the approach: wave 1.46 m, swell 1.36 m at "
        "10.4 s. No model reasoned over these figures \u2014 this summary is assembled "
        "mechanically from the AIS and marine fields above."
    ),
    "risk_reasoning": "(the same deterministic summary \u2014 see narrative_note)",
    "narrative_source": "deterministic_fallback",
    "narrative_note": "model call failed: The read operation timed out",
    "advisory": True,
    "scope_note": (
        "Advisory only. The counts, ETAs and ordering are computed deterministically from AIS "
        "fields; the narrative and risk reasoning are model-written prose about those numbers "
        "and are never parsed back into data. No vessel, MMSI or timestamp in this response was "
        "produced by a model."
    ),
}


@router.get(
    "/arrivals",
    response_model=ArrivalsBrief,
    summary="Port Louis arrivals brief from recent AIS positions",
    description=(
        "Expected arrivals in the next 24 hours, an approach-congestion summary, and "
        "weather-related risk reasoning for Port Louis.\n\n"
        "**Split of responsibility.** Counts, ETAs, the vessel list and its ordering are "
        "computed deterministically from AIS fields. The narrative and risk reasoning are "
        "written by the inference provider *about* those numbers and are never parsed back "
        "into structured data — no vessel, MMSI or timestamp in this response comes from a "
        "model. `narrative_source` reports which happened: `model` when the provider wrote "
        "grounded prose, `deterministic_fallback` when it was unavailable, simulated, or its "
        "output failed the grounding check (`narrative_note` then says why).\n\n"
        "**Honesty.** ETAs are self-reported by vessels over AIS, not port authority data and "
        "not a validated prediction. Terrestrial AIS coverage is nearshore and incomplete, so "
        "an empty brief means 'nothing observed', never 'nothing there'. Both statements ride "
        "in `provenance.coverage_note` on every response, and `provenance.data_kind` says "
        "whether the underlying positions are `live`, `cached`, `sample` or `synthetic`."
    ),
    responses={
        200: {
            "description": "Arrivals brief. Example is a real captured response.",
            "content": {"application/json": {"example": ARRIVALS_EXAMPLE}},
        },
        503: {"description": "Pillar registered but not enabled (PILLARS_ENABLED)."},
    },
)
async def arrivals(session: Session = Depends(get_session)) -> ArrivalsBrief:
    bundle = await transport_pillar.fetch({"session": session})
    return await transport_pillar.analyse(bundle)


@router.get(
    "/provenance",
    summary="Cheap data-source probe for the pillar index (no model inference)",
    description=(
        "Runs fetch() only and reports data_kind, source and coverage_note. Used by "
        "/pillars so the index can show at a glance which pillars are on live data "
        "and which are on samples/synthetic seeds, without paying for a full "
        "narrative call. No inference runs, so model_provider is reported as "
        "'not-invoked'."
    ),
)
async def provenance(session: Session = Depends(get_session)) -> dict:
    return await probe_provenance(transport_pillar, {"session": session})
