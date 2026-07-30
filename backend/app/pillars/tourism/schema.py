"""Result schema for the Sustainable Ocean Tourism pillar.

Subclasses PillarResult, so `provenance` is required by construction (Task 4a).

Field split is the honesty contract of this pillar, and it is load-bearing:
  * `measurements` and `ratings` are DETERMINISTIC — Open-Meteo values and
    suitability.py output. The model never writes into them.
  * `interpretation` is the ONLY model-written field.
A test (tests/test_pillar_tourism.py) pins that a model response cannot alter a
rating, mirroring how `legal_status` is protected in the fisheries pillar.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.pillars.base import PillarResult


class SiteMeasurements(BaseModel):
    """Straight from Open-Meteo. None means unavailable, never zero."""
    wave_height_m: Optional[float] = None
    wave_period_s: Optional[float] = None
    swell_height_m: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gusts_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    visibility_m: Optional[float] = None
    sea_surface_temperature_c: Optional[float] = None
    observed_at: Optional[str] = None


class ActivitySuitability(BaseModel):
    activity: str
    rating: str  # good | fair | poor | unknown
    score: int
    reasons: list[str] = Field(default_factory=list)


class SiteBrief(BaseModel):
    site_id: str
    name: str
    region: str
    character: str
    protected_area: bool = False
    protected_area_note: str = ""
    measurements: SiteMeasurements
    ratings: list[ActivitySuitability] = Field(default_factory=list)
    #: Model-written prose. Empty string when no provider was available — an
    #: empty brief is honest, an invented one is not.
    interpretation: str = ""
    #: "model" (fresh call), "cached" (served from narrative_cache without a
    #: model call), or "" (no interpretation — no provider, rejected output, or
    #: demo_mode with no cache entry yet).
    interpretation_source: str = ""


class TourismBrief(PillarResult):
    """One or more site briefs plus the honestly-scoped ranking."""
    sites: list[SiteBrief] = Field(default_factory=list)
    #: Present only when an activity was requested. Ordered best-first by the
    #: deterministic score.
    ranked_for_activity: Optional[str] = None
    ranking: list[dict] = Field(default_factory=list)
    #: Repeated on the result, not only in coverage_note, because this is the
    #: claim most likely to be over-read.
    ranking_basis: str = (
        "Ranking reflects forecast sea and wind conditions only. It uses NO "
        "visitor-count, crowding or occupancy data — none exists in this system."
    )
