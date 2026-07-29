"""Open-Meteo Marine client: timeout, bounded retry, cache, stale flag,
attribution, fallback location, deterministic mock, offline cached result.
Informational only — never a safety decision."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.limitations import MARINE_DISCLAIMER
from app.models.entities import MarineForecastCache

FALLBACK_LAT, FALLBACK_LON = -20.16, 57.50  # Mauritius west lagoon area (approximate)
HOURLY_VARS = "wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_direction,swell_wave_period,sea_surface_temperature"


def _location_key(lat: float, lon: float) -> str:
    return f"{round(lat, 2)},{round(lon, 2)}"


def _summarise(payload: dict) -> dict:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return {}
    idx = 0
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
    if now_iso in times:
        idx = times.index(now_iso)

    def val(name: str):
        vals = hourly.get(name) or []
        return vals[idx] if idx < len(vals) else None

    return {
        "time": times[idx],
        "wave_height_m": val("wave_height"),
        "wave_direction_deg": val("wave_direction"),
        "wave_period_s": val("wave_period"),
        "swell_height_m": val("swell_wave_height"),
        "swell_direction_deg": val("swell_wave_direction"),
        "swell_period_s": val("swell_wave_period"),
        "sea_surface_temperature_c": val("sea_surface_temperature"),
    }


def deterministic_mock(lat: float, lon: float) -> dict:
    seed = int(abs(lat * 100) + abs(lon * 100)) % 7
    return {
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00"),
        "wave_height_m": round(0.6 + seed * 0.15, 2),
        "wave_direction_deg": 120 + seed * 10,
        "wave_period_s": round(7.0 + seed * 0.5, 1),
        "swell_height_m": round(1.1 + seed * 0.2, 2),
        "swell_direction_deg": 190 + seed * 5,
        "swell_period_s": round(11.0 + seed * 0.4, 1),
        "sea_surface_temperature_c": round(24.0 + seed * 0.3, 1),
    }


def get_marine_conditions(session: Session, lat: float | None, lon: float | None, allow_network: bool = True) -> dict:
    settings = get_settings()
    lat = lat if lat is not None else FALLBACK_LAT
    lon = lon if lon is not None else FALLBACK_LON
    key = _location_key(lat, lon)
    cached = session.exec(
        select(MarineForecastCache).where(MarineForecastCache.location_key == key).order_by(MarineForecastCache.fetched_at.desc())  # type: ignore[union-attr]
    ).first()
    fresh_until = datetime.now(timezone.utc) - timedelta(minutes=settings.marine_cache_minutes)

    def _naive_utc(dt: datetime) -> datetime:
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    if cached and _naive_utc(cached.fetched_at) > _naive_utc(fresh_until):
        data = json.loads(cached.payload_json)
        data.update({"stale": False, "cached": True})
        return data

    if allow_network:
        url = f"{settings.marine_api_base}?latitude={lat}&longitude={lon}&hourly={HOURLY_VARS}&forecast_days=1"
        for _attempt in range(2):  # bounded retry
            try:
                r = httpx.get(url, timeout=10)
                r.raise_for_status()
                summary = _summarise(r.json())
                if summary:
                    data = {
                        "location": key, "source": "open-meteo",
                        "attribution": "Weather data by Open-Meteo.com (CC-BY 4.0)",
                        "disclaimer": MARINE_DISCLAIMER, "mock": False,
                        **summary,
                    }
                    session.add(MarineForecastCache(location_key=key, payload_json=json.dumps(data)))
                    session.commit()
                    data.update({"stale": False, "cached": False})
                    return data
            except (httpx.HTTPError, ValueError, KeyError):
                continue

    if cached:  # offline / failed: stale cache beats mock
        data = json.loads(cached.payload_json)
        data.update({"stale": True, "cached": True})
        return data

    data = {
        "location": key, "source": "deterministic-mock",
        "attribution": "Deterministic demonstration values (not a real forecast)",
        "disclaimer": MARINE_DISCLAIMER, "mock": True, "stale": False, "cached": False,
        **deterministic_mock(lat, lon),
    }
    return data
