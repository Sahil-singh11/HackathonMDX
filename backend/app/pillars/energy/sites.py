"""Candidate site catalogue for the energy pillar — data/energy/sites.json."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel

from app.core.config import get_settings


class CandidateSite(BaseModel):
    site_id: str
    name: str
    region: str
    latitude: float
    longitude: float
    exposure: str
    #: True for every current site; the deep-water formula caveat depends on it.
    nearshore: bool = True
    approx_distance_from_shore_km: float = 0.0


class SiteCatalogue(BaseModel):
    sites_version: str
    generated: str
    disclaimer: str
    coverage_note: str
    sites: list[CandidateSite]


@lru_cache(maxsize=1)
def load_sites() -> SiteCatalogue:
    path = get_settings().data_dir / "energy" / "sites.json"
    with open(path, encoding="utf-8") as f:
        return SiteCatalogue(**json.load(f))


def get_site(site_id: str) -> Optional[CandidateSite]:
    return next((s for s in load_sites().sites if s.site_id == site_id), None)
