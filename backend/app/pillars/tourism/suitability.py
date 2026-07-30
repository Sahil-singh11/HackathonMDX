"""Deterministic activity suitability — computed in Python, never by the model.

Same discipline as `legal_status` in the fisheries pillar: the number and the
verdict are code, the prose is the model's. A judge can re-derive every value
here by hand from the thresholds below, which is the whole point.

WHAT THIS IS NOT: it is not a crowding or load metric. There is no visitor-count
data anywhere in this project, so "spread visitors across less-strained sites"
cannot be answered directly. What is answerable is "given today's forecast, which
sites suit this activity" — which distributes people as a side effect and is
defensible under questioning. Every surface says so explicitly.

WHAT THE RATING IS ABOUT — read this before changing a threshold. The wave input
is OFFSHORE significant wave height from a model grid that answers up to 11 km
from the site, outside the reef. So a rating describes conditions OFFSHORE OF the
site, which is what governs boat access and how much swell reaches the lagoon —
it is NOT a measurement inside the lagoon, and the lagoon will be calmer. Bands
are anchored to the published WMO sea state code for that reason; see WAVE_BANDS.

Thresholds are NOT a safety standard and are labelled as such everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Activity = Literal["swimming", "snorkelling", "diving", "windsurfing", "kitesurfing"]
ACTIVITIES: tuple[Activity, ...] = ("swimming", "snorkelling", "diving", "windsurfing", "kitesurfing")

Rating = Literal["good", "fair", "poor", "unknown"]


@dataclass(frozen=True)
class Band:
    """Ideal and tolerable ranges for one measurement, for one activity."""
    good_max: float
    fair_max: float


# ---------------------------------------------------------------------------
# WAVE BANDS — calibrated for OFFSHORE significant wave height.
#
# These were originally lagoon numbers (snorkelling good <= 0.4 m) and they were
# wrong for the data they were fed. Open-Meteo's wave grid snaps a request by up
# to 11.2 km at Mauritius and answers from a point 0.9-8.7 km OFFSHORE, outside
# the fringing reef — measured 2026-07-30, with two sites collapsing into a
# single grid cell. So the input is open-ocean Hs, not lagoon chop, and judging
# open-ocean Hs against lagoon thresholds made every site "poor" regardless of
# conditions: the calmest reading in the catalogue (0.98 m) still exceeded
# snorkelling's old 0.8 m fair limit.
#
# The replacement is anchored to the WMO sea state code (Douglas scale), a
# published standard, NOT to numbers chosen to spread the colours:
#     state 2  smooth    0.10 - 0.50 m
#     state 3  slight    0.50 - 1.25 m
#     state 4  moderate  1.25 - 2.50 m
#     state 5  rough     2.50 - 4.00 m
#
# good = the activity is comfortable at this sea state offshore
# fair = workable for an experienced operator
# poor = rough (state 5+), or beyond what the activity tolerates
#
# Differentiation between activities is only where it is defensible: a diver
# descends below the chop, a snorkeller stays in it and needs surface visibility.
# ---------------------------------------------------------------------------
WAVE_BANDS: dict[str, Band] = {
    # slight / moderate — a swimmer offshore is in the chop
    "swimming": Band(good_max=1.25, fair_max=2.50),
    # slightly tighter: surface swimming plus the visibility a snorkeller needs
    "snorkelling": Band(good_max=1.25, fair_max=2.00),
    # more tolerant: the dive itself is below the surface chop
    "diving": Band(good_max=1.50, fair_max=2.50),
    # wind sports want some sea; these are upper limits, not targets
    "windsurfing": Band(good_max=2.50, fair_max=3.50),
    "kitesurfing": Band(good_max=2.50, fair_max=4.00),
}

#: WMO sea state boundaries, for reporting the state alongside the number.
WMO_SEA_STATE: list[tuple[float, str]] = [
    (0.10, "calm"), (0.50, "smooth"), (1.25, "slight"),
    (2.50, "moderate"), (4.00, "rough"), (6.00, "very rough"),
]


def sea_state(height_m: float | None) -> str:
    """Name the WMO sea state for a significant wave height."""
    if height_m is None:
        return "unknown"
    for limit, name in WMO_SEA_STATE:
        if height_m < limit:
            return name
    return "high"

WIND_BANDS_CALM: dict[str, Band] = {           # km/h, lower is better
    "swimming": Band(good_max=20.0, fair_max=32.0),
    "snorkelling": Band(good_max=16.0, fair_max=26.0),
    "diving": Band(good_max=22.0, fair_max=35.0),
}

# Wind sports need a MINIMUM. Below good_min it is not worth going out.
WIND_SPORT_MIN: dict[str, tuple[float, float]] = {  # (good_min, fair_min)
    "windsurfing": (18.0, 12.0),
    "kitesurfing": (20.0, 14.0),
}
WIND_SPORT_MAX = 55.0  # above this, wind sports are dangerous, not merely poor


@dataclass
class Conditions:
    """The deterministic inputs. None means "not available", never zero."""
    wave_height_m: Optional[float] = None
    wave_period_s: Optional[float] = None
    swell_height_m: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gusts_kmh: Optional[float] = None
    visibility_m: Optional[float] = None
    sea_surface_temperature_c: Optional[float] = None


@dataclass
class ActivityRating:
    activity: str
    rating: Rating
    """Plain-language reasons, each traceable to one threshold above."""
    reasons: list[str]
    """0-100, for ordering only. Never presented as a probability or a score
    with physical meaning."""
    score: int


def _rate_calm(activity: str, c: Conditions) -> ActivityRating:
    reasons: list[str] = []
    wave_band = WAVE_BANDS[activity]
    wind_band = WIND_BANDS_CALM[activity]

    if c.wave_height_m is None or c.wind_speed_kmh is None:
        return ActivityRating(activity, "unknown",
                              ["Offshore wave height or wind speed unavailable — not rated."], 0)

    wave, wind = c.wave_height_m, c.wind_speed_kmh
    wave_rating: Rating = ("good" if wave <= wave_band.good_max
                           else "fair" if wave <= wave_band.fair_max else "poor")
    wind_rating: Rating = ("good" if wind <= wind_band.good_max
                           else "fair" if wind <= wind_band.fair_max else "poor")

    reasons.append(
        f"Offshore wave height {wave:.2f} m — {sea_state(wave)} sea "
        f"({wave_rating}; good ≤ {wave_band.good_max} m)")
    reasons.append(f"Wind {wind:.0f} km/h ({wind_rating}; good ≤ {wind_band.good_max} km/h)")

    # The worse of the two governs: calm water is not calm if either is bad.
    order = {"good": 2, "fair": 1, "poor": 0, "unknown": 0}
    combined: Rating = min((wave_rating, wind_rating), key=lambda r: order[r])

    score = int(round(100 * (order[wave_rating] + order[wind_rating]) / 4))
    return ActivityRating(activity, combined, reasons, score)


def _rate_wind_sport(activity: str, c: Conditions) -> ActivityRating:
    reasons: list[str] = []
    if c.wind_speed_kmh is None:
        return ActivityRating(activity, "unknown", ["Wind speed unavailable — not rated."], 0)

    good_min, fair_min = WIND_SPORT_MIN[activity]
    wind = c.wind_speed_kmh

    if wind > WIND_SPORT_MAX:
        reasons.append(f"Wind {wind:.0f} km/h exceeds {WIND_SPORT_MAX:.0f} km/h — too strong.")
        return ActivityRating(activity, "poor", reasons, 0)

    if wind >= good_min:
        rating: Rating = "good"
    elif wind >= fair_min:
        rating = "fair"
    else:
        rating = "poor"
    reasons.append(f"Wind {wind:.0f} km/h ({rating}; good ≥ {good_min:.0f} km/h)")

    # Very big seas downgrade even a well-powered day.
    if c.wave_height_m is not None:
        band = WAVE_BANDS[activity]
        if c.wave_height_m > band.fair_max:
            reasons.append(
            f"Offshore wave height {c.wave_height_m:.2f} m — {sea_state(c.wave_height_m)} sea, "
            f"above {band.fair_max} m — downgraded.")
            rating = "poor"
        elif c.wave_height_m > band.good_max and rating == "good":
            reasons.append(
                f"Offshore wave height {c.wave_height_m:.2f} m above {band.good_max} m "
                f"— downgraded to fair.")
            rating = "fair"

    score = {"good": 100, "fair": 55, "poor": 10, "unknown": 0}[rating]
    return ActivityRating(activity, rating, reasons, score)


def rate_activity(activity: str, c: Conditions) -> ActivityRating:
    if activity in WIND_SPORT_MIN:
        return _rate_wind_sport(activity, c)
    if activity in WIND_BANDS_CALM:
        return _rate_calm(activity, c)
    return ActivityRating(activity, "unknown", [f"No thresholds defined for {activity!r}."], 0)


def rate_all(c: Conditions) -> list[ActivityRating]:
    return [rate_activity(a, c) for a in ACTIVITIES]


def rank_sites(site_conditions: list[tuple[str, Conditions]], activity: str) -> list[dict]:
    """Order sites for one activity, best first.

    Ordering only — the caller must present this as "conditions suit this
    activity", never as "go here instead, it is quieter". Ties keep input order,
    so the result is stable and reproducible.
    """
    scored = [
        {
            "site_id": site_id,
            "rating": r.rating,
            "score": r.score,
            "reasons": r.reasons,
        }
        for site_id, cond in site_conditions
        for r in (rate_activity(activity, cond),)
    ]
    return sorted(scored, key=lambda s: -int(s["score"]))
