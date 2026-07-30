"""Transit-window assessment for the Port Louis approach — deterministic, in Python.

Same honesty basis as energy/resource.py and tourism/suitability.py: every band a
user sees is decided HERE against fixed, stated thresholds, and the model is
handed the result and asked only for prose. Nothing in this module consults a
model, and no model output can change a band.

WHY THIS MODULE EXISTS. The transport pillar previously led with a vessel
arrivals list built from SYNTHETIC AIS, because aisstream.io carries no
Mauritius traffic — terrestrial AIS needs a receiver within roughly 40 nm and the
island has none, so the gap is physical, not a configuration mistake. Satellite
AIS covers it but is a paid product. Rather than keep presenting generated
vessels, the pillar now leads with the part that was always real: live
Open-Meteo sea state at the approach, turned into transit guidance.

WHAT THIS IS NOT
  - not a port authority clearance, and not a substitute for one
  - not a forecast of its own; it re-expresses someone else's forecast
  - not safety certification. Thresholds below are conservative planning
    heuristics for OPEN-WATER TRANSIT COMFORT AND FEASIBILITY, not survival
    limits, and they say nothing about a specific hull, load or crew.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

Band = Literal["good", "moderate", "poor", "unknown"]

#: Significant wave height bands, metres. Chosen for the two craft classes that
#: actually use this approach: open artisanal boats (the app's own users) and
#: commercial vessels. Values are planning conventions, stated so a reader can
#: disagree with them rather than having to reverse-engineer them.
SMALL_CRAFT_WAVE_M = {"good": 1.25, "moderate": 2.0}      # above moderate -> poor
LARGE_VESSEL_WAVE_M = {"good": 2.5, "moderate": 4.0}

#: Wind bands, km/h. 1 kn ~= 1.852 km/h; 20 kn ~= 37 km/h is the conventional
#: comfort ceiling for a small open boat, 33 kn ~= 61 km/h is near gale.
SMALL_CRAFT_WIND_KMH = {"good": 28.0, "moderate": 46.0}
LARGE_VESSEL_WIND_KMH = {"good": 46.0, "moderate": 74.0}

#: A long swell period with modest height still produces a big, slow heave that
#: matters far more to a small boat than the height alone suggests. Flagged
#: rather than folded into the band, so the reason stays visible.
LONG_SWELL_PERIOD_S = 12.0
LONG_SWELL_MIN_HEIGHT_M = 1.0


def _band(value: Optional[float], thresholds: dict[str, float]) -> Band:
    """Fixed-threshold band. `None` is `unknown`, never an assumed value."""
    if value is None:
        return "unknown"
    if value <= thresholds["good"]:
        return "good"
    if value <= thresholds["moderate"]:
        return "moderate"
    return "poor"


def _worst(*bands: Band) -> Band:
    """Weakest link, with `unknown` outranking every positive band.

    Precedence is `poor` > `unknown` > `moderate` > `good`, and the middle term
    is the important one:

      - a KNOWN-bad reading dominates. If the sea is poor, the window is poor
        whether or not the wind reading arrived; saying so is both safe and
        more informative than "unknown".
      - otherwise a MISSING reading blocks any positive claim. With `unknown`
        ordered last (the original bug) `_worst("unknown", "good")` returned
        "good", so an absent wave height reported a GOOD transit window for a
        small open boat — the single most dangerous output this module could
        produce. Pinned by
        test_a_missing_reading_is_unknown_and_never_treated_as_calm.
    """
    order = ["poor", "unknown", "moderate", "good"]
    for b in order:
        if b in bands:
            return b
    return "unknown"


@dataclass
class CraftAssessment:
    """One craft class's window, with the driver named."""
    craft: str
    wave_band: Band
    wind_band: Band
    overall: Band
    #: Which input decided `overall`, so a surprising band is explainable.
    limiting_factor: str
    thresholds_note: str


@dataclass
class TransitWindow:
    wave_height_m: Optional[float]
    wave_period_s: Optional[float]
    swell_height_m: Optional[float]
    swell_period_s: Optional[float]
    wind_speed_kmh: Optional[float]
    wind_gusts_kmh: Optional[float]
    sea_surface_temperature_c: Optional[float]
    crafts: list[CraftAssessment] = field(default_factory=list)
    long_swell_flag: bool = False
    long_swell_note: str = ""
    #: True when any input was missing, so bands are partly `unknown`.
    incomplete: bool = False


def assess(marine: dict, wind: dict) -> TransitWindow:
    """Build the assessment from one marine reading and one wind reading.

    Both dicts come straight from the app's existing Open-Meteo clients. Missing
    keys stay missing: a band of `unknown` is honest, a defaulted 0 is not.
    """
    wave = marine.get("wave_height_m")
    swell = marine.get("swell_height_m")
    swell_period = marine.get("swell_period_s")
    gusts = wind.get("wind_gusts_kmh")
    speed = wind.get("wind_speed_kmh")

    # Gusts govern when they are known: a boat is knocked down by the gust, not
    # by the ten-minute mean.
    effective_wind = gusts if gusts is not None else speed

    crafts: list[CraftAssessment] = []
    for craft, wave_t, wind_t in (
        ("Small open craft (artisanal fishing boat)", SMALL_CRAFT_WAVE_M, SMALL_CRAFT_WIND_KMH),
        ("Commercial vessel", LARGE_VESSEL_WAVE_M, LARGE_VESSEL_WIND_KMH),
    ):
        wb = _band(wave, wave_t)
        nb = _band(effective_wind, wind_t)
        overall = _worst(wb, nb)
        if overall == "unknown":
            limiting = "a required reading was unavailable"
        elif wb == overall and nb != overall:
            limiting = "wave height"
        elif nb == overall and wb != overall:
            limiting = "wind" + (" (gusts)" if gusts is not None else "")
        else:
            limiting = "wave height and wind together"
        crafts.append(CraftAssessment(
            craft=craft, wave_band=wb, wind_band=nb, overall=overall,
            limiting_factor=limiting,
            thresholds_note=(
                f"good <= {wave_t['good']} m wave and <= {wind_t['good']} km/h wind; "
                f"moderate <= {wave_t['moderate']} m and <= {wind_t['moderate']} km/h; "
                f"above either is poor"
            ),
        ))

    long_swell = bool(
        swell_period is not None and swell_period >= LONG_SWELL_PERIOD_S
        and swell is not None and swell >= LONG_SWELL_MIN_HEIGHT_M
    )

    return TransitWindow(
        wave_height_m=wave,
        wave_period_s=marine.get("wave_period_s"),
        swell_height_m=swell,
        swell_period_s=swell_period,
        wind_speed_kmh=speed,
        wind_gusts_kmh=gusts,
        sea_surface_temperature_c=marine.get("sea_surface_temperature_c"),
        crafts=crafts,
        long_swell_flag=long_swell,
        long_swell_note=(
            f"Swell is running {swell} m at {swell_period} s. A period at or above "
            f"{LONG_SWELL_PERIOD_S} s produces a long, slow heave that a small open boat "
            f"feels much more than the height alone suggests."
            if long_swell else ""
        ),
        incomplete=any(v is None for v in (wave, effective_wind)),
    )
