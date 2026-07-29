"""Marine Transport & Trade — the pillar module.

Government pillar naming verbatim: "Marine Transport & Trade".

What this pillar claims: a port brief for Port Louis assembled from AIS
messages, with a model-written narrative on top of deterministic numbers.

What it does NOT claim, in the payload as well as here:

* ETAs are **self-reported by vessels over AIS**, plus reasoning over
  conditions. This is not a validated predictive model and not port authority
  data. A crew types the destination and ETA by hand; both are routinely stale,
  abbreviated or wrong.
* **Terrestrial AIS coverage is nearshore and incomplete.** Vessels out of
  receiver range, with AIS switched off, or transmitting only Class B are
  absent. An empty brief means "nothing seen", never "nothing there".

Both sentences ride in `coverage_note` on every response, because a caller who
only ever reads the JSON must still get them.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.inference.registry import select as select_provider
from app.pillars.base import PillarResult, RawBundle, SourceDescriptor
from app.pillars.provenance import DataProvenance
from app.pillars.transport import ais, brief, store
from app.services.marine.client import get_marine_conditions

log = logging.getLogger(__name__)

PILLAR_ID = "transport"
PILLAR_NAME = "Marine Transport & Trade"

SOURCE_AISSTREAM = SourceDescriptor(
    name="aisstream.io",
    url="https://aisstream.io",
    description=("Real-time AIS WebSocket, bounding-box subscription over Port Louis and "
                 "its approach. Until a live message is captured, the pillar serves a "
                 "committed synthetic capture constructed from the documented message "
                 "schema and labelled data_kind='synthetic'."),
    status="candidate",
)
SOURCE_MARINE = SourceDescriptor(
    name="Open-Meteo Marine",
    url="https://marine-api.open-meteo.com/v1/marine",
    description="Sea state at the port approach; already integrated and cached by the app.",
    status="verified",
)

# The two honesty sentences required by Task 4b §4. Kept as one constant so
# they cannot drift between the payload and the documentation.
COVERAGE_NOTE = (
    "ETAs are self-reported by vessels over AIS plus reasoning over conditions — "
    "not a validated predictive model, and not port authority data. "
    "Terrestrial AIS coverage is nearshore and incomplete: vessels out of receiver "
    "range, with AIS switched off, or transmitting Class B only are absent, so an "
    "empty or thin brief means 'nothing observed', never 'nothing there'. "
    "Live AIS via aisstream was probed on 30 Jul 2026 — global stream flowing, zero "
    "messages for the Mauritius region — so this deployment serves schema-accurate "
    "synthetic data until a covered feed exists. "
    "This brief does not confirm any berth allocation, clearance or port call."
)

SCOPE_NOTE = (
    "Advisory only. The counts, ETAs and ordering are computed deterministically from "
    "AIS fields; the narrative and risk reasoning are model-written prose about those "
    "numbers and are never parsed back into data. No vessel, MMSI or timestamp in this "
    "response was produced by a model."
)


# --------------------------------------------------------------------------
# Result schema
# --------------------------------------------------------------------------

class ArrivalEntry(BaseModel):
    mmsi: int
    vessel_name: Optional[str] = None
    identity_known: bool
    vessel_type: str
    nav_status: str
    destination_reported: Optional[str] = None
    reported_eta_utc: str
    hours_to_reported_eta: float
    distance_nm: float
    speed_knots: Optional[float] = None
    draught_m: Optional[float] = None
    last_seen_utc: str


class CongestionSummary(BaseModel):
    vessels_tracked: int
    under_way: int
    at_anchor: int
    moored: int
    other_or_unknown_status: int
    within_approach_radius: int
    approach_radius_nm: float
    identity_unknown: int
    note: str


class PortDescriptor(BaseModel):
    name: str
    unlocode: str
    latitude: float
    longitude: float


class ArrivalsBrief(PillarResult):
    """The transport pillar's result. `provenance` is inherited and required."""

    port: PortDescriptor
    window_hours: int
    expected_arrivals: list[ArrivalEntry]
    expected_arrivals_count: int
    congestion: CongestionSummary
    conditions: dict
    narrative: str
    risk_reasoning: str
    narrative_source: str = Field(
        description=("'model' when an inference provider wrote the prose and it passed the "
                     "grounding check; 'deterministic_fallback' when it did not, or when no "
                     "real provider was available. Never silently one or the other."),
    )
    narrative_note: str = ""
    advisory: bool = True
    scope_note: str = SCOPE_NOTE


# --------------------------------------------------------------------------
# The module
# --------------------------------------------------------------------------

class TransportPillar:
    pillar_id = PILLAR_ID
    pillar_name = PILLAR_NAME
    result_schema = ArrivalsBrief

    def sources(self) -> list[SourceDescriptor]:
        return [SOURCE_AISSTREAM, SOURCE_MARINE]

    # -- fetch --------------------------------------------------------------
    async def fetch(self, params: dict) -> RawBundle:
        """Read the rolling AIS window, seeding it from the synthetic capture
        when no observation has ever been collected.

        Degradation is recorded, never hidden: the bundle's data_kind is the
        weakest kind actually present in the rows served, so a window holding
        only synthetic seed data can never be labelled live.
        """
        params = params or {}
        session: Optional[Session] = params.get("session")
        now = params.get("now") or datetime.now(timezone.utc)
        settings = get_settings()

        owns_session = session is None
        session = session or Session(get_engine())
        try:
            rows = store.latest_per_vessel(session, now=now)
            if not rows:
                path = settings.data_dir / "pillars" / "transport" / "ais_synthetic_port_louis.json"
                messages, _declared = ais.load_synthetic(path, now)
                observations = ais.normalise(messages, now)
                store.record(session, observations, "synthetic", now=now)
                rows = store.latest_per_vessel(session, now=now)

            kinds = {r.data_kind for r in rows}
            # Weakest-link labelling. "live" only when every row served is live.
            if not kinds or kinds == {"synthetic"}:
                data_kind = "synthetic"
            elif "synthetic" in kinds:
                data_kind = "synthetic"
            elif "sample" in kinds:
                data_kind = "sample"
            elif kinds == {"live"}:
                data_kind = "live"
            else:
                data_kind = "cached"

            conditions = get_marine_conditions(
                session, ais.PORT_LOUIS_LAT, ais.PORT_LOUIS_LON,
                allow_network=params.get("allow_network", True),
            )
        finally:
            if owns_session:
                session.close()

        # SQLite round-trips datetimes without tzinfo, so the newest received_at
        # comes back naive. Re-attach UTC rather than emitting an unqualified
        # timestamp: provenance.retrieved_at is how a reader judges staleness,
        # and a bare local-looking string invites the wrong reading.
        newest = max((r.received_at for r in rows), default=now)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)

        return RawBundle(
            pillar_id=PILLAR_ID,
            source=SOURCE_AISSTREAM,
            retrieved_at=newest,
            data_kind=data_kind,
            coverage_note=COVERAGE_NOTE,
            payload={
                "rows": rows,
                "conditions": conditions,
                "now": now,
                "window_hours": settings.transport_arrivals_window_hours,
            },
        )

    # -- analyse ------------------------------------------------------------
    async def analyse(self, bundle: RawBundle) -> ArrivalsBrief:
        payload: dict[str, Any] = bundle.payload or {}
        rows = payload.get("rows") or []
        conditions = payload.get("conditions") or {}
        now: datetime = payload.get("now") or datetime.now(timezone.utc)
        window_hours: int = payload.get("window_hours") or 24

        # --- deterministic half: never model-touched ------------------------
        arrivals = brief.expected_arrivals(rows, now=now, window_hours=window_hours)
        congestion = brief.congestion(rows)
        known_mmsis = {r.mmsi for r in rows}

        # --- model half: prose only ----------------------------------------
        narrative, risk, source, note, provider_name = self._narrate(
            arrivals, congestion, conditions, window_hours=window_hours,
            data_kind=bundle.data_kind, known_mmsis=known_mmsis,
        )

        return ArrivalsBrief(
            pillar_id=PILLAR_ID,
            generated_at=now,
            provenance=DataProvenance(
                source_name=bundle.source.name,
                source_url=bundle.source.url,
                retrieved_at=bundle.retrieved_at,
                data_kind=bundle.data_kind,
                model_provider=provider_name,
                coverage_note=bundle.coverage_note,
            ),
            port=PortDescriptor(name=brief.PORT_NAME, unlocode=brief.PORT_UNLOCODE,
                                latitude=ais.PORT_LOUIS_LAT, longitude=ais.PORT_LOUIS_LON),
            window_hours=window_hours,
            expected_arrivals=[ArrivalEntry(**a) for a in arrivals],
            expected_arrivals_count=len(arrivals),
            congestion=CongestionSummary(**congestion),
            conditions=conditions,
            narrative=narrative,
            risk_reasoning=risk,
            narrative_source=source,
            narrative_note=note,
        )

    def _narrate(self, arrivals: list[dict], congestion: dict, conditions: dict, *,
                 window_hours: int, data_kind: str,
                 known_mmsis: set[int]) -> tuple[str, str, str, str, str]:
        """Returns (narrative, risk_reasoning, source, note, provider_name).

        Every path that does not end in grounded model prose falls back to the
        deterministic summary AND says why. There is no path where the caller
        cannot tell which happened.
        """
        fallback = brief.deterministic_narrative(arrivals, congestion, conditions,
                                                 window_hours=window_hours)

        try:
            provider, _events = select_provider()
            health = provider.health_check()
            provider_name = provider.name
        except Exception as exc:  # noqa: BLE001 — selection must never 500 the route
            log.warning("transport: provider selection failed: %s", exc)
            return fallback, fallback, "deterministic_fallback", f"provider selection failed: {exc}", "none"

        if not health.available or health.simulated:
            why = ("the selected provider is a disclosed mock, so no model reasoned over this brief"
                   if health.simulated else f"provider unavailable: {health.detail}")
            return fallback, fallback, "deterministic_fallback", why, provider_name

        prompt = brief.build_prompt(arrivals, congestion, conditions,
                                    window_hours=window_hours, data_kind=data_kind)
        try:
            text = (provider.chat(prompt) or "").strip()
        except Exception as exc:  # noqa: BLE001 — a model outage degrades, never 500s
            log.warning("transport: provider chat failed: %s", exc)
            return fallback, fallback, "deterministic_fallback", f"model call failed: {exc}", provider_name

        ok, reason = brief.narrative_is_grounded(text, known_mmsis)
        if not ok:
            log.warning("transport: narrative rejected — %s", reason)
            return fallback, fallback, "deterministic_fallback", f"model output rejected: {reason}", provider_name

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        narrative = paragraphs[0] if paragraphs else text
        risk = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else ""
        if not risk:
            # One paragraph came back where two were asked for. Say so rather
            # than splitting prose arbitrarily and pretending it was structured.
            return (narrative, fallback, "model",
                    "model returned a single paragraph; risk reasoning fell back to the "
                    "deterministic summary", provider_name)
        return narrative, risk, "model", "", provider_name


transport_pillar = TransportPillar()
