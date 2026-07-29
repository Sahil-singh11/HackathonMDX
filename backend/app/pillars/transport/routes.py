"""Transport pillar routes, mounted at /api/pillars/transport/.

The enabled-check (503 while disabled) and the per-IP throttle are applied by
`PillarRegistry.mount_all`, not here — this router declares only what is
specific to the pillar.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.pillars.transport.module import ArrivalsBrief, transport_pillar

router = APIRouter()

# A REAL captured response, trimmed to two arrivals for readability. Taken from
# `GET /api/pillars/transport/arrivals` with the synthetic seed and the default
# mock provider — which is why `narrative_source` is `deterministic_fallback`
# and `data_kind` is `synthetic`. Nothing here was written by hand to look good:
# an example that does not match what the endpoint returns is worse than none.
ARRIVALS_EXAMPLE = {
    "pillar_id": "transport",
    "generated_at": "2026-07-29T22:22:54.009606Z",
    "provenance": {
        "source_name": "aisstream.io",
        "source_url": "https://aisstream.io",
        "retrieved_at": "2026-07-29T22:22:54.009606Z",
        "data_kind": "synthetic",
        "model_provider": "mock",
        "coverage_note": (
            "ETAs are self-reported by vessels over AIS plus reasoning over conditions — not a "
            "validated predictive model, and not port authority data. Terrestrial AIS coverage "
            "is nearshore and incomplete: vessels out of receiver range, with AIS switched off, "
            "or transmitting Class B only are absent, so an empty or thin brief means 'nothing "
            "observed', never 'nothing there'. This brief does not confirm any berth "
            "allocation, clearance or port call."
        ),
    },
    "port": {"name": "Port Louis", "unlocode": "MUPLU", "latitude": -20.158, "longitude": 57.488},
    "window_hours": 24,
    "expected_arrivals": [
        {
            "mmsi": 645123456, "vessel_name": "MSC LORETO", "identity_known": True,
            "vessel_type": "cargo", "nav_status": "under way using engine",
            "destination_reported": "PORT LOUIS",
            "reported_eta_utc": "2026-07-30T10:00:00+00:00", "hours_to_reported_eta": 11.6,
            "distance_nm": 6.36, "speed_knots": 11.4, "draught_m": 11.2,
            "last_seen_utc": "2026-07-29T22:22:54.009606+00:00",
        },
        {
            "mmsi": 645234567, "vessel_name": "CMA CGM MASCAREIGNE", "identity_known": True,
            "vessel_type": "cargo", "nav_status": "under way using engine",
            "destination_reported": "PORT LOUIS",
            "reported_eta_utc": "2026-07-30T14:30:00+00:00", "hours_to_reported_eta": 16.1,
            "distance_nm": 10.66, "speed_knots": 14.1, "draught_m": 12.8,
            "last_seen_utc": "2026-07-29T22:22:54.009606+00:00",
        },
    ],
    "expected_arrivals_count": 5,
    "congestion": {
        "vessels_tracked": 12, "under_way": 9, "at_anchor": 2, "moored": 1,
        "other_or_unknown_status": 0, "within_approach_radius": 8,
        "approach_radius_nm": 10.0, "identity_unknown": 2,
        "note": ("Counts are every vessel in the retention window, tallied by AIS navigational "
                 "status. 'identity_unknown' vessels sent a position but no static data, so "
                 "their name, type, destination and ETA are genuinely unknown — they are "
                 "counted, never named or guessed."),
    },
    "conditions": {
        "location": "-20.16,57.49", "source": "deterministic-mock", "mock": True,
        "wave_height_m": 1.46, "swell_height_m": 1.36, "swell_period_s": 10.4,
        "sea_surface_temperature_c": 24.9,
    },
    "narrative": (
        "5 vessel(s) report Port Louis as their destination within the next 24 hours; the "
        "earliest is MSC LORETO, reported ETA 2026-07-30T10:00:00+00:00. 12 vessel(s) are "
        "tracked in the window: 9 under way, 2 at anchor, 1 moored, 2 without identifying "
        "static data. … No model reasoned over these figures — this summary is assembled "
        "mechanically from the AIS and marine fields above."
    ),
    "risk_reasoning": "(same deterministic summary — no model reasoned over this brief)",
    "narrative_source": "deterministic_fallback",
    "narrative_note": "the selected provider is a disclosed mock, so no model reasoned over this brief",
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
