"""Result schema for the Ocean-Based Renewable Energy pillar.

Field split, as in tourism: `resource` and `measurements` are computed or
measured, `interpretation` is the only model-written field. A test proves a model
response cannot alter a computed figure.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.pillars.base import PillarResult


class SiteMeasurements(BaseModel):
    """Raw Open-Meteo values. None means unavailable, never zero."""
    wave_height_m: Optional[float] = None
    wave_period_s: Optional[float] = None
    swell_height_m: Optional[float] = None
    swell_period_s: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gusts_kmh: Optional[float] = None
    observed_at: Optional[str] = None


class SiteResource(BaseModel):
    """Computed by app.pillars.energy.resource. The model never writes here."""
    wave_power_kw_per_m: Optional[float] = None
    wind_power_w_per_m2: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    #: Why the wave figure is indicative rather than accurate.
    period_basis: str = ""
    #: Why the wind figure understates a real turbine's resource.
    wind_height_basis: str = ""


class SiteAssessment(BaseModel):
    site_id: str
    name: str
    region: str
    exposure: str
    nearshore: bool = True
    approx_distance_from_shore_km: float = 0.0
    measurements: SiteMeasurements
    resource: SiteResource
    #: The written note. Always populated by build_brief() — model prose when the
    #: model produced usable prose, otherwise a summary assembled from the figures.
    interpretation: str = ""
    #: Which rung produced the note. FOUR values, because two changes landed on
    #: this field in parallel and each drew a distinction the other conflated:
    #:
    #:   'model'                 a fresh model call wrote it
    #:   'cached'                real, already-grounded model prose reused from
    #:                           narrative_cache without paying for a second call
    #:   'deterministic_fallback' assembled in code from the computed figures
    #:   'none'                  no note was produced at all
    #:
    #: 'cached' is NOT a lesser rung than 'model' — it is the same model prose,
    #: already checked by prose_or_empty and numeric_guard before it was stored.
    #: The UI must therefore treat model and cached alike when it says who wrote a
    #: sentence, and must NOT show a mechanical-summary badge for cached text.
    #:
    #: 'none' rather than '' as the default, and kept distinct from
    #: 'deterministic_fallback': the default describes an unpopulated object, and
    #: claiming a source for text that does not exist is the same class of
    #: overclaim as presenting a template as model reasoning.
    interpretation_source: str = "none"


class EnergyBrief(PillarResult):
    sites: list[SiteAssessment] = Field(default_factory=list)
    #: Sites ordered by computed wave power, best first. Ordering only.
    comparison: list[dict] = Field(default_factory=list)
    #: Repeated on the result, not only in coverage_note, because "resource
    #: assessment" is the phrase most likely to be over-read as a yield study.
    assessment_basis: str = (
        "Forecast-window resource indication computed from a public weather model. "
        "This is NOT a bankable yield assessment and NOT a site survey. It does not "
        "account for bathymetry, seabed conditions, grid access, marine protected "
        "areas, shipping lanes, consenting or cabling. Deep-water formulas are used "
        "at nearshore points, which overstates the wave figure."
    )
    formulas: dict = Field(default_factory=dict)
