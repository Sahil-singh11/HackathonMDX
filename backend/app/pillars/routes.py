"""Pillar API routes.

Task 4a ships exactly one route — the registry listing — plus the builder
that future pillar modules mount into. Pillar routes carry the same per-IP
throttle mechanism as /api/analyse-catch, but in their OWN bucket: the
listing is cheap metadata the frontend may poll, and it must never be able
to starve the analyse budget (10/min) that the demo depends on. Deliberate
choice, recorded here and in the PR body.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.core.ratelimit import InMemoryRateLimiter
from app.pillars import numeric_guard
from app.pillars.registry import PillarRegistry, pillar_registry

log = logging.getLogger(__name__)

# Own bucket (see module docstring). Same class, same 429 + Retry-After shape.
_pillars_limiter = InMemoryRateLimiter(limit=30, window_seconds=60.0)


def reset_limiters() -> None:
    """Called by /api/demo/reset alongside the analyse limiter."""
    _pillars_limiter.reset()
    numeric_guard.stats.reset()


def _client_ip(request: Request) -> str:
    """Best-effort client address behind a reverse proxy.

    Same logic as app.api.routes._client_ip (X-Forwarded-For first, because
    Render fronts the app as a reverse proxy). Duplicated deliberately:
    pillars must not import app.api.routes — that module imports half the
    application, and the dependency has to point the other way.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def build_pillar_router(registry: Optional[PillarRegistry] = None,
                        limiter: Optional[InMemoryRateLimiter] = None) -> APIRouter:
    """Build the pillar router: the /api/pillars listing plus every
    implemented pillar router mounted under /api/pillars/{pillar_id} behind
    the enabled-check + throttle guard. Injectable registry/limiter so the
    contract tests exercise mounting against a fresh instance without
    touching the app-wide singletons."""
    reg = registry if registry is not None else pillar_registry
    lim = limiter if limiter is not None else _pillars_limiter
    router = APIRouter()

    @router.get(
        "/api/pillars",
        tags=["pillars"],
        summary="List the six national blue-economy pillars and their state",
        description=(
            "All six pillars of the national Blue Economy strategy, government "
            "naming verbatim. `status: live` means implemented AND enabled via "
            "settings (PILLARS_ENABLED); everything else is registered-but-"
            "disabled. Declared data sources carry an honesty status "
            "(verified | candidate | none)."
        ),
    )
    def list_pillars(request: Request) -> dict:
        if not lim.allow(_client_ip(request)):
            raise HTTPException(
                429,
                "Too many pillar requests from this address — please wait a minute and try again.",
                headers={"Retry-After": "60"},
            )
        items = [d.model_dump() for d in reg.list()]
        return {
            "pillars": items,
            "count": len(items),
            "note": (
                "Pillar results always carry a DataProvenance block: source, "
                "retrieval time, data_kind (live|cached|sample|synthetic), "
                "inference provider, and what the data does not cover."
            ),
        }

    @router.get(
        "/api/pillars/diagnostics/numeric-guard",
        tags=["pillars"],
        summary="Number-firewall counters: narratives checked, rejected, and why",
        description=(
            "Every model-written pillar narrative (energy, tourism, transport) is "
            "checked against the figures it was actually given before being shown to "
            "anyone; a number that cannot be traced back to those figures is dropped "
            "and the pillar falls back to a figures-only or mechanical summary. "
            "In-memory since the last restart or /api/demo/reset — a demo counter, "
            "not a durability guarantee."
        ),
    )
    def numeric_guard_stats(request: Request) -> dict:
        if not lim.allow(_client_ip(request)):
            raise HTTPException(
                429,
                "Too many pillar requests from this address — please wait a minute and try again.",
                headers={"Retry-After": "60"},
            )
        return numeric_guard.stats.snapshot()

    # NOTE for future pillar owners: fisheries deliberately does NOT get a
    # /provenance route here. It predates the PillarModule contract (Task 4a
    # §5) and has no fetch()/analyse() to probe — any signal built for it
    # (e.g. proxying the marine cache) would be a guessed stand-in, not fisheries'
    # own data_kind. test_pillar_probe.py::test_a_pillar_without_the_convention_...
    # pins the resulting 404 as intentional: the index renders an absence
    # rather than inventing a label. Tried and reverted — see decision log.

    reg.mount_all(router, lim, _client_ip)
    return router
