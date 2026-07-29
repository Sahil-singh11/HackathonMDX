"""Sustainable Ocean Tourism pillar (Workstream 2).

`register_tourism()` is called once from app.main before build_pillar_router(),
which keeps registration explicit and avoids an import cycle through
app.pillars.__init__.
"""
from __future__ import annotations

import logging

from app.pillars.registry import PillarRegistry, pillar_registry

log = logging.getLogger(__name__)


def register_tourism(registry: PillarRegistry | None = None) -> None:
    """Attach the tourism module and its router to a declared descriptor.

    Idempotent: safe to call twice (tests build their own app instances).
    Registering does NOT enable the pillar — it still has to be listed in
    PILLARS_ENABLED, otherwise its routes answer 503.
    """
    from app.pillars.tourism.module import tourism_pillar
    from app.pillars.tourism.routes import router as tourism_router

    reg = registry if registry is not None else pillar_registry
    if tourism_pillar.pillar_id in getattr(reg, "_modules", {}):
        return
    reg.register_module(tourism_pillar, tourism_router)


def prewarm_tourism_sites() -> None:
    """Warm the condition cache for every named site.

    Runs on a worker thread from main (never on the event loop), and staggers
    requests so eight sites x two endpoints does not arrive at Open-Meteo as one
    burst. Sleeping here costs nothing: /health is already answering.

    Three of the sites share coordinates with the existing marine pre-warm
    (Grand Baie, Flic-en-Flac, Mahebourg), so those marine keys are usually
    already warm and only the wind half is fetched.
    """
    import time

    from sqlmodel import Session

    from app.db.session import get_engine
    from app.pillars.tourism.sites import load_sites
    from app.pillars.tourism.wind import get_wind_conditions
    from app.services.marine.client import get_marine_conditions

    for site in load_sites().sites:
        try:
            # One short-lived session per site, matching _run_marine_prewarm:
            # a single long transaction across eight network calls would hold a
            # SQLite connection open for the whole pre-warm.
            with Session(get_engine()) as session:
                get_marine_conditions(session, site.latitude, site.longitude)
                get_wind_conditions(session, site.latitude, site.longitude)
            log.info("Tourism cache pre-warmed for %s", site.name)
        except Exception:  # noqa: BLE001 — startup must never crash on this
            log.warning("Tourism pre-warm failed for %s", site.name, exc_info=True)
        time.sleep(0.25)  # be a polite API client
