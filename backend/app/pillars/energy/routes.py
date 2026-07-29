"""Energy pillar routes, mounted at /api/pillars/energy by registry.mount_all.

The mount helper applies the enabled check (503 until listed in PILLARS_ENABLED)
and the shared per-IP throttle, so neither is re-implemented here.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_session
from app.pillars.energy.module import energy_pillar
from app.pillars.energy.sites import load_sites

router = APIRouter()


@router.get("/sites", summary="Candidate coastal points used for resource figures")
def list_sites() -> dict:
    cat = load_sites()
    return {
        "sites_version": cat.sites_version,
        "generated": cat.generated,
        "disclaimer": cat.disclaimer,
        "coverage_note": cat.coverage_note,
        "sites": [s.model_dump() for s in cat.sites],
    }


@router.get(
    "/resource",
    summary="Wave and wind resource indication for candidate sites",
    description=(
        "Wave power density (0.49*H^2*T kW/m) and wind power density "
        "(0.5*rho*v^3 W/m^2) computed in Python from Open-Meteo values. The model "
        "writes prose only and cannot produce or alter a figure. This is a "
        "forecast-window indication, not a yield assessment or a site survey."
    ),
)
async def resource(
    site_ids: Optional[str] = Query(
        default=None, description="Comma-separated site ids. Omit for every candidate site."
    ),
    session: Session = Depends(get_session),
) -> dict:
    wanted = [s.strip() for s in site_ids.split(",") if s.strip()] if site_ids else None
    if wanted is not None:
        known = {s.site_id for s in load_sites().sites}
        unknown = [s for s in wanted if s not in known]
        if unknown:
            raise HTTPException(404, f"unknown site id(s): {unknown}")

    bundle = await energy_pillar.fetch({"session": session, "site_ids": wanted})
    result = await energy_pillar.analyse(bundle)
    return result.model_dump(mode="json")
