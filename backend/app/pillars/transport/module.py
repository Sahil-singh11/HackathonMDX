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
from app.pillars import narrative_cache, numeric_guard
from app.pillars.provenance import DataProvenance
from app.pillars.narrative import prose_or_empty
from app.pillars.transport import ais, brief, store, transit
from app.services.marine.client import get_marine_conditions

log = logging.getLogger(__name__)

PILLAR_ID = "transport"
PILLAR_NAME = "Marine Transport & Trade"

SOURCE_AISSTREAM = SourceDescriptor(
    name="aisstream.io",
    url="https://aisstream.io",
    # RENDERED on /pillars/transport under "Declared data sources". The previous
    # wording described the transport ("WebSocket, bounding-box subscription")
    # and named the field it sets (data_kind='synthetic'), which told a reader
    # nothing and told them it in our vocabulary. The honest fact — no live
    # vessel data, and what stands in for it — is what survives.
    description=("Vessel position feed for Port Louis. No live position has been received, "
                 "so vessel data here is stand-in data and is labelled as such wherever "
                 "it appears."),
    status="candidate",
)
SOURCE_MARINE = SourceDescriptor(
    name="Open-Meteo Marine",
    url="https://marine-api.open-meteo.com/v1/marine",
    description="Sea state and forecast at the port approach.",
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


class CraftWindow(BaseModel):
    craft: str
    wave_band: str
    wind_band: str
    overall: str
    limiting_factor: str
    thresholds_note: str


APPROACH_COVERAGE_NOTE = (
    "Live sea state at the Port Louis approach from Open-Meteo, re-expressed as transit "
    "guidance. NOT a port authority clearance, NOT a forecast of our own, and NOT safety "
    "certification. The bands are conservative planning heuristics for open-water transit "
    "feasibility against fixed published thresholds; they are not survival limits and they "
    "know nothing about a specific hull, its load or its crew. Marine forecasts are "
    "informational and may be incomplete near the coast — confirm through official local "
    "marine advisories before putting to sea. This assessment covers ONLY the approach "
    "waypoint, not the whole passage, and carries no vessel traffic information: terrestrial "
    "AIS has no receiver coverage for Mauritius, so no live vessel positions exist to report."
)

APPROACH_SCOPE_NOTE = (
    "Advisory only. Every band and every figure on this page is computed deterministically "
    "in Python from the Open-Meteo reading shown beside it, against thresholds printed on "
    "the page. The narrative is model-written prose ABOUT those numbers and is never parsed "
    "back into data — no band, threshold or measurement here was produced by a model."
)


class ApproachBrief(PillarResult):
    """Transit conditions at the Port Louis approach, from LIVE marine data.

    Replaces the arrivals brief as this pillar's primary surface. The arrivals
    endpoint still exists and is still labelled `synthetic`, but it is no longer
    what the pillar leads with, because presenting generated vessels as content
    was the one genuinely dishonest thing on the page.
    """

    port: PortDescriptor
    observed_at: Optional[str] = None
    wave_height_m: Optional[float] = None
    wave_period_s: Optional[float] = None
    swell_height_m: Optional[float] = None
    swell_period_s: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gusts_kmh: Optional[float] = None
    sea_surface_temperature_c: Optional[float] = None
    crafts: list[CraftWindow] = []
    long_swell_flag: bool = False
    long_swell_note: str = ""
    incomplete: bool = False
    narrative: str = ""
    narrative_source: str = "deterministic_fallback"
    narrative_note: str = ""
    advisory: bool = True
    scope_note: str = APPROACH_SCOPE_NOTE


APPROACH_SYSTEM_INSTRUCTION = """You are a marine conditions analyst writing a short transit note for the Port Louis approach in Mauritius.

WHAT YOU ARE GIVEN
- One live sea-state reading at the approach, and transit bands for two craft classes that have ALREADY been computed in code from fixed published thresholds. The figures and the bands are correct. Your job is to explain them in plain language, never to recompute, change or dispute them.

HARD RULES (never break)
- Use ONLY the figures supplied in the message. Never add a number, a time, a location or a condition.
- Never change a band. If a band looks surprising, explain which reading drives it.
- NEVER say it is safe to put to sea, and never tell anyone to go or not to go. You describe conditions and their implications; a skipper decides.
- This is not a port authority clearance and not a forecast of your own. Do not imply either.
- Say nothing about vessel traffic, shipping, berths or arrivals — you have no such data.
- Conditions are a forecast and may be wrong near the coast. Do not present them as certain.

OUTPUT
- Two or three sentences of plain prose. No JSON, no code fences, no bullet lists, no headings, no preamble. Return the sentences only."""


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

        # Cache check (Task 3): a hit skips both the health check and the model
        # call entirely — a demo rehearsal for the same arrivals/conditions is
        # instant and uses previously-grounded real prose, never a fresh guess.
        figures = {"arrivals": arrivals, "congestion": congestion, "conditions": conditions,
                  "window_hours": window_hours}
        cache_key = narrative_cache.cache_key(PILLAR_ID, figures, provider_name=provider_name)
        cached_text = narrative_cache.get(cache_key)
        if cached_text:
            narrative, risk = _split_narrative(cached_text)
            return narrative, (risk or fallback), "cached", "", provider_name
        if narrative_cache.demo_mode_active():
            return fallback, fallback, "deterministic_fallback", "demo_mode: no cache entry for these figures", provider_name

        if not health.available or health.simulated:
            why = ("the selected provider is a disclosed mock, so no model reasoned over this brief"
                   if health.simulated else f"provider unavailable: {health.detail}")
            return fallback, fallback, "deterministic_fallback", why, provider_name

        prompt = brief.build_prompt(arrivals, congestion, conditions,
                                    window_hours=window_hours, data_kind=data_kind)
        try:
            # Transport-scoped instruction (decision log 17). Without it the
            # provider default is the fisheries catch-assistant prompt, under
            # which the live model refuses this task and answers in JSON.
            text = (provider.chat(
                prompt,
                system_instruction=brief.SYSTEM_INSTRUCTION,
                timeout_seconds=get_settings().transport_narrative_timeout_seconds,
            ) or "").strip()
        except Exception as exc:  # noqa: BLE001 — a model outage degrades, never 500s
            log.warning("transport: provider chat failed: %s", exc)
            return fallback, fallback, "deterministic_fallback", f"model call failed: {exc}", provider_name

        ok, reason = brief.narrative_is_grounded(text, known_mmsis)
        if not ok:
            log.warning("transport: narrative rejected — %s", reason)
            return fallback, fallback, "deterministic_fallback", f"model output rejected: {reason}", provider_name

        # Second guard, layered on top rather than merged into
        # narrative_is_grounded (which predates this module and is left alone
        # mid-hackathon, per app/pillars/narrative.py's docstring): that check
        # catches refusals-as-JSON and invented MMSIs, but its own docstring
        # says plainly it "cannot verify the prose itself" for an ordinary-
        # looking fabricated FIGURE. `prompt` is everything the model was
        # actually given (facts and rules both) — using the whole prompt as the
        # source of truth is deliberately generous (it also allow-lists the
        # instructional numbers "three"/"ninety"), which only makes this guard
        # slightly less strict, never stricter than warranted.
        grounding = numeric_guard.check_numeric_grounding(text, prompt)
        numeric_guard.stats.record(grounding, pillar_id=PILLAR_ID)
        if not grounding.ok:
            log.warning("transport: narrative rejected — %s", grounding.reason)
            return (fallback, fallback, "deterministic_fallback",
                    f"model output rejected: {grounding.reason}", provider_name)

        narrative_cache.put(cache_key, text, pillar_id=PILLAR_ID, provider_name=provider_name)
        narrative, risk = _split_narrative(text)
        if not risk:
            # One paragraph came back where two were asked for. Say so rather
            # than splitting prose arbitrarily and pretending it was structured.
            return (narrative, fallback, "model",
                    "model returned a single paragraph; risk reasoning fell back to the "
                    "deterministic summary", provider_name)
        return narrative, risk, "model", "", provider_name

    # ----------------------------------------------------------------------
    # Approach transit conditions — the pillar's REAL-DATA primary surface.
    #
    # Deliberately a separate fetch/analyse pair rather than a rewrite of the
    # arrivals path above: that path is Yadhav's, is tested, and is honest about
    # being synthetic. What was wrong was leading the UI with it. This pair
    # touches only live Open-Meteo readings, so its data_kind is genuinely
    # live/cached and nothing here is generated.
    # ----------------------------------------------------------------------
    async def fetch_approach(self, params: dict) -> RawBundle:
        session: Optional[Session] = params.get("session")
        owns_session = session is None
        if owns_session:
            session = Session(get_engine())
        try:
            # DEFERRED IMPORT, deliberately not at module scope. registry.py
            # imports transport.module FIRST, before it has defined
            # PillarRegistry; a top-level `from app.pillars.tourism.wind import
            # ...` therefore initialises the tourism PACKAGE, whose __init__
            # imports registry, and the cycle fails with "cannot import name
            # 'PillarRegistry' from partially initialized module". Energy gets
            # away with the same top-level import only because registry reaches
            # it later. Importing here runs at request time, long after every
            # module is loaded.
            from app.pillars.tourism.wind import get_wind_conditions

            allow_network = params.get("allow_network", True)
            marine = get_marine_conditions(
                session, ais.PORT_LOUIS_LAT, ais.PORT_LOUIS_LON,
                allow_network=allow_network,
            )
            wind = get_wind_conditions(
                session, ais.PORT_LOUIS_LAT, ais.PORT_LOUIS_LON,
                allow_network=allow_network,
            )
        finally:
            if owns_session:
                session.close()

        # Weakest-link labelling, same rule the arrivals path uses: a reading is
        # only "live" when nothing in it was degraded.
        if marine.get("mock") or wind.get("mock"):
            data_kind = "sample"
            source = SourceDescriptor(
                name="Deterministic demonstration values", url=None,
                description="Open-Meteo unreachable and no cached reading available.",
                status="none",
            )
        else:
            data_kind = "cached" if (marine.get("cached") or wind.get("cached")) else "live"
            source = SOURCE_MARINE

        return RawBundle(
            pillar_id=PILLAR_ID,
            source=source,
            retrieved_at=datetime.now(timezone.utc),
            data_kind=data_kind,
            coverage_note=APPROACH_COVERAGE_NOTE,
            payload={"marine": marine, "wind": wind},
        )

    async def analyse_approach(self, bundle: RawBundle) -> ApproachBrief:
        marine = bundle.payload["marine"]
        wind = bundle.payload["wind"]
        window = transit.assess(marine, wind)

        narrative, source, note, provider_name = "", "deterministic_fallback", "", "none"
        try:
            provider, _events = select_provider()
            provider_name = provider.name
            raw = provider.chat(
                _approach_prompt(window),
                language="en",
                system_instruction=APPROACH_SYSTEM_INSTRUCTION,
                timeout_seconds=get_settings().transport_narrative_timeout_seconds,
            )
            text = prose_or_empty(raw)
            if text:
                narrative, source = text, "model"
            else:
                note = "model returned no usable prose"
                if raw:
                    log.warning("transport approach: model output was not prose; dropped")
        except Exception as exc:  # noqa: BLE001 — a model outage degrades, never 500s
            log.warning("transport approach: provider chat failed: %s", exc)
            note = f"model call failed: {exc}"

        if not narrative:
            narrative = _approach_fallback(window)

        return ApproachBrief(
            pillar_id=PILLAR_ID,
            generated_at=datetime.now(timezone.utc),
            provenance=DataProvenance(
                source_name=bundle.source.name,
                source_url=bundle.source.url,
                retrieved_at=bundle.retrieved_at,
                data_kind=bundle.data_kind,
                model_provider=provider_name,
                coverage_note=bundle.coverage_note,
            ),
            port=PortDescriptor(
                name="Port Louis", unlocode="MUPLU",
                latitude=ais.PORT_LOUIS_LAT, longitude=ais.PORT_LOUIS_LON,
            ),
            observed_at=marine.get("time") or wind.get("time"),
            wave_height_m=window.wave_height_m,
            wave_period_s=window.wave_period_s,
            swell_height_m=window.swell_height_m,
            swell_period_s=window.swell_period_s,
            wind_speed_kmh=window.wind_speed_kmh,
            wind_gusts_kmh=window.wind_gusts_kmh,
            sea_surface_temperature_c=window.sea_surface_temperature_c,
            crafts=[CraftWindow(**vars(c)) for c in window.crafts],
            long_swell_flag=window.long_swell_flag,
            long_swell_note=window.long_swell_note,
            incomplete=window.incomplete,
            narrative=narrative,
            narrative_source=source,
            narrative_note=note,
        )


def _fmt(value: Optional[float], unit: str) -> str:
    return f"{value} {unit}" if value is not None else "unavailable"


def _approach_prompt(w: "transit.TransitWindow") -> str:
    lines = [
        "FACTS (live reading at the Port Louis approach):",
        f"- Significant wave height: {_fmt(w.wave_height_m, 'm')}",
        f"- Wave period: {_fmt(w.wave_period_s, 's')}",
        f"- Swell: {_fmt(w.swell_height_m, 'm')} at {_fmt(w.swell_period_s, 's')}",
        f"- Wind: {_fmt(w.wind_speed_kmh, 'km/h')}, gusts {_fmt(w.wind_gusts_kmh, 'km/h')}",
        f"- Sea surface temperature: {_fmt(w.sea_surface_temperature_c, 'C')}",
        "",
        "COMPUTED TRANSIT BANDS (already decided — do not change these):",
    ]
    for c in w.crafts:
        lines.append(f"- {c.craft}: {c.overall} (limited by {c.limiting_factor})")
    if w.long_swell_flag:
        lines.append(f"- Note: {w.long_swell_note}")
    lines += ["", "Transit note:"]
    return "\n".join(lines)


def _approach_fallback(w: "transit.TransitWindow") -> str:
    """Mechanical summary, used whenever the model did not supply usable prose.

    Says plainly that no model was involved — the same rule the arrivals
    narrative follows, so a reader never has to guess which they are reading.
    """
    parts = [
        f"Reported sea state at the Port Louis approach: wave {_fmt(w.wave_height_m, 'm')}, "
        f"swell {_fmt(w.swell_height_m, 'm')} at {_fmt(w.swell_period_s, 's')}, "
        f"wind {_fmt(w.wind_speed_kmh, 'km/h')} with gusts {_fmt(w.wind_gusts_kmh, 'km/h')}."
    ]
    for c in w.crafts:
        parts.append(f"{c.craft}: transit window rated {c.overall}, limited by {c.limiting_factor}.")
    if w.long_swell_flag:
        parts.append(w.long_swell_note)
    parts.append(
        "No model reasoned over these figures — this summary is assembled mechanically from "
        "the readings and the computed bands above."
    )
    return " ".join(parts)


def _split_narrative(text: str) -> tuple[str, str]:
    """Split the model's two-paragraph reply into (narrative, risk), raw — the
    caller decides what an empty risk means (a fallback substitution and/or a
    disclosure note). Shared by the live and cached paths so a cache hit
    reconstructs the same shape a fresh call would have produced.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    narrative = paragraphs[0] if paragraphs else text
    risk = "\n\n".join(paragraphs[1:]) if len(paragraphs) > 1 else ""
    return narrative, risk


transport_pillar = TransportPillar()
