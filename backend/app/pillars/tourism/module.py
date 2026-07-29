"""Sustainable Ocean Tourism pillar module.

Implements the PillarModule protocol frozen at Task 4a. Import boundary: this
file touches `app.inference.registry` only — never a provider module or a model
SDK (enforced by tests/test_pillar_contract.py).

THE DIVISION OF LABOUR, which is the point of this pillar:
  fetch()   — Open-Meteo values, cached, degraded honestly (live/cached/sample)
  suitability.py — every rating and score, computed in Python
  analyse() — asks the model for PROSE ONLY, then discards anything it says
              about numbers by never reading its output into a rating field

If no provider is available the brief still returns, with an empty
interpretation. A missing sentence is honest; a fabricated one is not.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from app.core.limitations import MARINE_DISCLAIMER
# Imported as the fully-qualified module (not `from app.inference import
# registry`), because the Task 4a boundary test allows exactly
# "app.inference.registry" and reads the latter form as importing
# "app.inference". Binding the module rather than `select` also keeps it
# patchable in tests.
import app.inference.registry as inference_registry
from app.pillars.base import RawBundle, SourceDescriptor
from app.pillars.provenance import DataProvenance
from app.pillars.tourism import wind as wind_client
from app.pillars.tourism.schema import (ActivitySuitability, SiteBrief,
                                        SiteMeasurements, TourismBrief)
from app.pillars.tourism.sites import Site, load_sites
from app.pillars.tourism.suitability import Conditions, rank_sites, rate_all
from app.services.marine.client import get_marine_conditions

log = logging.getLogger(__name__)

PILLAR_ID = "tourism"
PILLAR_NAME = "Sustainable Ocean Tourism"  # government naming, verbatim

#: How many sites get a model-written brief per request. Bounds worst-case
#: latency: hosted Gemma is ~20-30 s per call, so this is the difference between
#: a usable request and a multi-minute one.
MAX_INTERPRETED_SITES = 3

_MARINE_SOURCE = SourceDescriptor(
    name="Open-Meteo Marine",
    url="https://marine-api.open-meteo.com/v1/marine",
    description="Wave, swell and sea-surface temperature. Already integrated and cached.",
    status="verified",
)
_FORECAST_SOURCE = SourceDescriptor(
    name="Open-Meteo Forecast",
    url="https://api.open-meteo.com/v1/forecast",
    description=("Wind speed/direction/gusts and visibility. Separate host from the marine "
                 "endpoint, which carries no atmospheric wind."),
    status="verified",
)


def _coverage_note(has_protected: bool) -> str:
    note = (
        "Forecast sea state and weather only. Carries NO information about visitor numbers, "
        "crowding or occupancy — no such data exists in this system, so the ranking reflects "
        "conditions alone. Also excludes water quality, pollution, jellyfish and other marine "
        "hazards, lifeguard presence, reef health, and whether access is permitted. "
        "Model output at a rounded coordinate for a general beach area, not a measurement at "
        "any specific spot. " + MARINE_DISCLAIMER
    )
    if has_protected:
        note += (" One or more sites lie in a marine protected area whose activity rules are "
                 "NOT encoded in this app — check with the authorities before entering the water.")
    return note


class TourismPillar:
    """PillarModule implementation for ocean tourism condition briefs."""

    pillar_id = PILLAR_ID
    pillar_name = PILLAR_NAME
    result_schema = TourismBrief

    def sources(self) -> list[SourceDescriptor]:
        return [_MARINE_SOURCE, _FORECAST_SOURCE]

    # -- fetch --------------------------------------------------------------
    async def fetch(self, params: dict) -> RawBundle:
        """Gather deterministic conditions for the requested sites.

        `params`: session (required), site_ids (optional list), allow_network
        (defaults True; tests pass False so the default suite makes no network
        calls).
        """
        session: Session = params["session"]
        allow_network: bool = params.get("allow_network", True)
        wanted: Optional[list[str]] = params.get("site_ids")

        catalogue = load_sites()
        sites = [s for s in catalogue.sites if wanted is None or s.site_id in wanted]

        readings: list[dict] = []
        degraded_to_sample = False
        any_cached = False

        for site in sites:
            marine = get_marine_conditions(session, site.latitude, site.longitude,
                                           allow_network=allow_network)
            breeze = wind_client.get_wind_conditions(session, site.latitude, site.longitude,
                                                     allow_network=allow_network)
            if marine.get("mock") or breeze.get("mock"):
                degraded_to_sample = True
            if marine.get("cached") or breeze.get("cached"):
                any_cached = True
            readings.append({"site": site, "marine": marine, "wind": breeze})

        # Never label data fresher than it is: any mock anywhere makes the whole
        # bundle a sample, and any cache hit makes it cached.
        data_kind = "sample" if degraded_to_sample else ("cached" if any_cached else "live")

        return RawBundle(
            pillar_id=PILLAR_ID,
            source=_MARINE_SOURCE if not degraded_to_sample else SourceDescriptor(
                name="Deterministic demonstration values", url=None,
                description="Open-Meteo unreachable and no cached reading available.",
                status="none"),
            retrieved_at=datetime.now(timezone.utc),
            data_kind=data_kind,
            coverage_note=_coverage_note(any(s.protected_area for s in sites)),
            payload={"readings": readings, "activity": params.get("activity")},
        )

    # -- analyse ------------------------------------------------------------
    async def analyse(self, bundle: RawBundle) -> TourismBrief:
        readings = bundle.payload["readings"]
        activity: Optional[str] = bundle.payload.get("activity")

        briefs: list[SiteBrief] = []
        site_conditions: list[tuple[str, Conditions]] = []

        for entry in readings:
            site: Site = entry["site"]
            marine, breeze = entry["marine"], entry["wind"]

            cond = Conditions(
                wave_height_m=marine.get("wave_height_m"),
                wave_period_s=marine.get("wave_period_s"),
                swell_height_m=marine.get("swell_height_m"),
                wind_speed_kmh=breeze.get("wind_speed_kmh"),
                wind_gusts_kmh=breeze.get("wind_gusts_kmh"),
                visibility_m=breeze.get("visibility_m"),
                sea_surface_temperature_c=marine.get("sea_surface_temperature_c"),
            )
            site_conditions.append((site.site_id, cond))

            # Every rating is computed here, in Python. Nothing below reads model
            # output into these fields.
            ratings = [ActivitySuitability(activity=r.activity, rating=r.rating,
                                           score=r.score, reasons=r.reasons)
                       for r in rate_all(cond)]

            briefs.append(SiteBrief(
                site_id=site.site_id, name=site.name, region=site.region,
                character=site.character,
                protected_area=site.protected_area,
                protected_area_note=site.protected_area_note,
                measurements=SiteMeasurements(
                    wave_height_m=cond.wave_height_m,
                    wave_period_s=cond.wave_period_s,
                    swell_height_m=cond.swell_height_m,
                    wind_speed_kmh=cond.wind_speed_kmh,
                    wind_gusts_kmh=cond.wind_gusts_kmh,
                    wind_direction_deg=breeze.get("wind_direction_deg"),
                    visibility_m=cond.visibility_m,
                    sea_surface_temperature_c=cond.sea_surface_temperature_c,
                    observed_at=marine.get("time") or breeze.get("time"),
                ),
                ratings=ratings,
            ))

        ranking: list[dict] = []
        if activity:
            ranking = rank_sites(site_conditions, activity)

        # One model call per site would make a full-catalogue brief unusable:
        # hosted Gemma runs ~20-30 s per call, so eight sites is minutes of
        # latency. Interpret only the top few (ranking order when an activity was
        # given, otherwise catalogue order). The rest return figures with an empty
        # interpretation, which is a state the schema and UI already handle
        # honestly — better a missing sentence than a four-minute request.
        order = [r["site_id"] for r in ranking] if ranking else [b.site_id for b in briefs]
        by_id = {b.site_id: b for b in briefs}
        to_interpret = [by_id[sid] for sid in order[:MAX_INTERPRETED_SITES] if sid in by_id]

        provider_name = "none"
        try:
            provider, _events = inference_registry.select()
            provider_name = provider.name
            for brief in to_interpret:
                brief.interpretation = self._interpret(provider, brief)
        except Exception:  # noqa: BLE001 — a brief without prose is still valid
            log.warning("Tourism interpretation unavailable; returning figures only", exc_info=True)

        return TourismBrief(
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
            sites=briefs,
            ranked_for_activity=activity,
            ranking=ranking,
        )

    # -- the model's only job ----------------------------------------------
    @staticmethod
    def _interpret(provider, brief: SiteBrief) -> str:
        """Ask for prose about figures that are already decided.

        The prompt hands over the computed ratings and forbids new numbers. Even
        if the model ignores that, its text lands in `interpretation` only — no
        code path copies it into a measurement or a rating.
        """
        m = brief.measurements
        facts = [
            f"Site: {brief.name} ({brief.region}). {brief.character}",
            f"Wave height: {m.wave_height_m} m" if m.wave_height_m is not None else "Wave height: unavailable",
            f"Wave period: {m.wave_period_s} s" if m.wave_period_s is not None else "Wave period: unavailable",
            f"Wind: {m.wind_speed_kmh} km/h, gusts {m.wind_gusts_kmh} km/h" if m.wind_speed_kmh is not None else "Wind: unavailable",
            f"Visibility: {m.visibility_m} m" if m.visibility_m is not None else "Visibility: unavailable",
            f"Sea temperature: {m.sea_surface_temperature_c} C" if m.sea_surface_temperature_c is not None else "Sea temperature: unavailable",
            "Computed suitability (already decided — do not change these): "
            + "; ".join(f"{r.activity}={r.rating}" for r in brief.ratings),
        ]
        prompt = (
            "You write short condition briefs for ocean-tourism operators in Mauritius.\n\n"
            "RULES:\n"
            "1. Do NOT state any number that is not in the FACTS below. Never invent a figure.\n"
            "2. Do NOT change or dispute the computed suitability ratings — explain them.\n"
            "3. Two or three sentences. Plain language for an operator deciding today's plan.\n"
            "4. Say nothing about how busy or crowded the site is — you have no such data.\n"
            "5. This is not safety advice; do not tell anyone it is safe to enter the water.\n\n"
            "FACTS:\n" + "\n".join(facts) + "\n\nBrief:"
        )
        try:
            return (provider.chat(prompt, language="en") or "").strip()
        except Exception:  # noqa: BLE001
            log.warning("Interpretation failed for %s", brief.site_id, exc_info=True)
            return ""


tourism_pillar = TourismPillar()
