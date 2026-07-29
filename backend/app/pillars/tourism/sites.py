"""Tourism site catalogue — loaded from data/tourism/sites.json.

Same pattern as the species catalogue and rules files: versioned JSON on disk is
the source of truth, never a database table (see DECISION_LOG entry 12).
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel

from app.core.config import get_settings


class Site(BaseModel):
    site_id: str
    name: str
    region: str
    latitude: float
    longitude: float
    character: str
    typical_activities: list[str]
    protected_area: bool = False
    protected_area_note: str = ""


class SiteCatalogue(BaseModel):
    sites_version: str
    generated: str
    disclaimer: str
    coverage_note: str
    sites: list[Site]


@lru_cache(maxsize=1)
def load_sites() -> SiteCatalogue:
    path = get_settings().data_dir / "tourism" / "sites.json"
    with open(path, encoding="utf-8") as f:
        return SiteCatalogue(**json.load(f))


def get_site(site_id: str) -> Optional[Site]:
    return next((s for s in load_sites().sites if s.site_id == site_id), None)


def public_site(site: Site) -> dict:
    """Site as exposed over the API. Coordinates are already approximate area
    centres (2 dp is all the forecast lookup needs), so they are safe to
    publish — unlike catch positions, these are public beaches."""
    return {
        "site_id": site.site_id,
        "name": site.name,
        "region": site.region,
        "latitude": round(site.latitude, 4),
        "longitude": round(site.longitude, 4),
        "character": site.character,
        "typical_activities": site.typical_activities,
        "protected_area": site.protected_area,
        "protected_area_note": site.protected_area_note,
    }
