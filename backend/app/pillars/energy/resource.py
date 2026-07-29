"""Wave and wind resource formulas — deterministic, in Python, never the model.

This module is the whole honesty basis of the energy pillar. Every number a user
sees is produced here and unit-tested against hand-worked values; the model is
given the results and asked for prose. It is the same rule as `legal_status` in
the fisheries pillar and the suitability ratings in tourism.

--------------------------------------------------------------------------------
WAVE POWER DENSITY (per metre of wave crest), deep water:

    P = 0.49 * H^2 * Te     [kW/m]

  H  = significant wave height [m]
  Te = ENERGY period [s]

  The 0.49 constant folds rho*g^2/(64*pi) for seawater into kW.

  !! THE PERIOD PROBLEM — read before trusting any figure from this module.
  The formula requires the energy period Te. Open-Meteo's `wave_period` is
  documented only as "Period between mean, wind and swell waves" (checked
  2026-07-30); it is NOT identified as an energy period. Conventionally
  Te ~= 0.86-0.9 * Tp (peak) but Te ~= 1.1-1.2 * Tm02 (mean), so the two
  readings pull the answer in OPPOSITE directions by roughly 10-20%.

  We therefore use the supplied period AS-IS and label the output indicative,
  rather than applying a conversion factor that would imply we know which period
  we were given. `period_basis` on every result records this, and the coverage
  note states the resulting uncertainty. Guessing the factor would make the
  number look more precise while being no more correct.

  Also: this is the DEEP-WATER form. It overestimates in shallow water, where
  shoaling, refraction and bottom friction all matter. Mauritius candidate sites
  are nearshore, so every figure carries that caveat too.

--------------------------------------------------------------------------------
WIND POWER DENSITY (per square metre of swept area):

    P = 0.5 * rho * v^3     [W/m^2]

  rho = air density [kg/m^3], 1.225 at sea level, 15 C (ISA)
  v   = wind speed [m/s] at the measurement height

  !! UNIT TRAP: Open-Meteo returns wind in km/h. Because the relationship is
  CUBIC, feeding km/h in as if it were m/s inflates the answer by 3.6^3 = 46.7x.
  `wind_power_density` takes m/s only and there is an explicit conversion
  helper, with a test pinning the 46.7x error it prevents.

  Also: v is measured at 10 m (Open-Meteo's standard height), not at hub height.
  Real turbine hubs sit 80-150 m up where wind is stronger, so a 10 m figure
  UNDERSTATES the resource available to a real machine. No shear extrapolation is
  applied here — that needs a roughness/stability assumption this data cannot
  support.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: Seawater constant for the deep-water wave-power formula, folded to kW/m.
WAVE_POWER_COEFFICIENT = 0.49

#: ISA sea-level air density [kg/m^3].
AIR_DENSITY_KG_M3 = 1.225

#: Open-Meteo's wind measurement height [m].
WIND_MEASUREMENT_HEIGHT_M = 10.0

#: km/h -> m/s. Named because getting this wrong is a 46.7x error.
KMH_TO_MS = 1.0 / 3.6


def kmh_to_ms(speed_kmh: float) -> float:
    """Convert km/h to m/s. Mandatory before wind_power_density."""
    return speed_kmh * KMH_TO_MS


def wave_power_density(significant_height_m: float, period_s: float) -> float:
    """Deep-water wave power per metre of crest, kW/m.

    Uses the period as supplied — see the module docstring on why no energy-period
    conversion is applied. Negative or zero inputs return 0.0 rather than a
    nonsensical value.
    """
    if significant_height_m <= 0 or period_s <= 0:
        return 0.0
    return WAVE_POWER_COEFFICIENT * (significant_height_m ** 2) * period_s


def wind_power_density(speed_ms: float, air_density: float = AIR_DENSITY_KG_M3) -> float:
    """Wind power per square metre of swept area, W/m^2.

    Takes SPEED IN m/s. Passing km/h here overstates the result by 46.7x.
    """
    if speed_ms <= 0:
        return 0.0
    return 0.5 * air_density * (speed_ms ** 3)


@dataclass
class ResourceEstimate:
    """One site's computed resource. Every field is code-derived."""
    wave_power_kw_per_m: Optional[float] = None
    wind_power_w_per_m2: Optional[float] = None
    #: Inputs echoed back so a reader can re-derive the figures by hand.
    significant_height_m: Optional[float] = None
    period_s: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    #: Records that the period was used as supplied, not converted to Te.
    period_basis: str = (
        "Open-Meteo wave_period used as supplied; the source does not identify it "
        "as an energy period, so the wave figure is indicative only (~10-20% "
        "uncertainty in either direction)."
    )
    wind_height_basis: str = (
        "Wind measured at 10 m, not hub height; a real turbine at 80-150 m would "
        "see more. No shear extrapolation applied."
    )


def estimate(significant_height_m: Optional[float], period_s: Optional[float],
             wind_speed_kmh: Optional[float]) -> ResourceEstimate:
    """Compute both densities from raw Open-Meteo values.

    None inputs stay None in the output — a missing measurement is reported as
    missing, never defaulted to zero, because 0 kW/m is a real physical claim.
    """
    wave = (wave_power_density(significant_height_m, period_s)
            if significant_height_m is not None and period_s is not None else None)

    wind_ms = kmh_to_ms(wind_speed_kmh) if wind_speed_kmh is not None else None
    wind = wind_power_density(wind_ms) if wind_ms is not None else None

    return ResourceEstimate(
        wave_power_kw_per_m=round(wave, 2) if wave is not None else None,
        wind_power_w_per_m2=round(wind, 1) if wind is not None else None,
        significant_height_m=significant_height_m,
        period_s=period_s,
        wind_speed_ms=round(wind_ms, 2) if wind_ms is not None else None,
        wind_speed_kmh=wind_speed_kmh,
    )


def compare(estimates: list[tuple[str, ResourceEstimate]]) -> list[dict]:
    """Order sites by wave power, best first. Ordering only — this is a forecast
    resource indication, never a siting recommendation."""
    return sorted(
        [
            {
                "site_id": site_id,
                "wave_power_kw_per_m": e.wave_power_kw_per_m,
                "wind_power_w_per_m2": e.wind_power_w_per_m2,
            }
            for site_id, e in estimates
        ],
        key=lambda d: -(d["wave_power_kw_per_m"] or 0.0),
    )
