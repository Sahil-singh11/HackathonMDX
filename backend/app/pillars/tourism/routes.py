"""Tourism pillar routes, mounted at /api/pillars/tourism by registry.mount_all.

The mount helper already applies the enabled check (503 while the pillar is not
in PILLARS_ENABLED) and the shared per-IP throttle, so nothing here re-implements
either.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_session
from app.pillars.tourism.module import tourism_pillar
from app.pillars.tourism.sites import load_sites, public_site
from app.pillars.tourism.suitability import ACTIVITIES

router = APIRouter()


@router.get("/sites", summary="Named reef and beach sites covered by this pillar")
def list_sites() -> dict:
    cat = load_sites()
    return {
        "sites_version": cat.sites_version,
        "generated": cat.generated,
        "disclaimer": cat.disclaimer,
        "coverage_note": cat.coverage_note,
        "activities": list(ACTIVITIES),
        "sites": [public_site(s) for s in cat.sites],
    }


@router.get("/brief", summary="Condition briefs, with optional activity ranking")
async def brief(
    site_ids: Optional[str] = Query(
        default=None,
        description="Comma-separated site ids. Omit for every site.",
    ),
    activity: Optional[str] = Query(
        default=None,
        description=(
            "One of: " + ", ".join(ACTIVITIES) + ". When given, sites are ranked "
            "best-first on FORECAST CONDITIONS ONLY — never on crowding, which "
            "this system has no data for."
        ),
    ),
    session: Session = Depends(get_session),
) -> dict:
    if activity is not None and activity not in ACTIVITIES:
        raise HTTPException(422, f"unknown activity {activity!r}; expected one of {list(ACTIVITIES)}")

    wanted = [s.strip() for s in site_ids.split(",") if s.strip()] if site_ids else None
    if wanted is not None:
        known = {s.site_id for s in load_sites().sites}
        unknown = [s for s in wanted if s not in known]
        if unknown:
            raise HTTPException(404, f"unknown site id(s): {unknown}")

    bundle = await tourism_pillar.fetch(
        {"session": session, "site_ids": wanted, "activity": activity}
    )
    result = await tourism_pillar.analyse(bundle)
    return result.model_dump(mode="json")
