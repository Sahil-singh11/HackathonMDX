"""Pillar registry — discovery, enable/disable via settings, route mounting.

All six national blue-economy pillars are declared here (Task 4a), using the
government's own naming verbatim. Exactly one is live today: Sustainable
Fisheries & Aquaculture, served by the existing production routes and
deliberately NOT refactored into a module (Task 4a §5 — it works and it is
judged). The other five are registered-but-disabled descriptors until their
owner lands an implementation and flips them on via settings.

Enable/disable is config-driven: `PILLARS_ENABLED` is a comma-separated list
of pillar ids allowed to serve live routes (default: "fisheries"). A pillar
is `enabled` only when it is implemented AND listed there — so merging a
module never silently exposes it.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.ratelimit import InMemoryRateLimiter
from app.pillars.base import PillarModule, SourceDescriptor
from app.pillars.transport.module import transport_pillar
from app.pillars.transport.routes import router as transport_router

log = logging.getLogger(__name__)


class PillarDescriptor(BaseModel):
    """What /api/pillars reports for one pillar."""

    pillar_id: str = Field(min_length=1)
    pillar_name: str = Field(min_length=1)  # government naming, verbatim
    status: str = "registered"              # "live" | "registered" (derived in list())
    enabled: bool = False                   # derived in list()
    implemented: bool = False
    owner: str = ""
    description: str = ""
    sources: list[SourceDescriptor] = []
    endpoints: list[str] = []


def _enabled_ids_from_settings() -> set[str]:
    raw = get_settings().pillars_enabled
    return {p.strip() for p in raw.split(",") if p.strip()}


class PillarRegistry:
    """Holds descriptors, attaches implementations, mounts routers."""

    def __init__(self, enabled_ids: Optional[Callable[[], set[str]]] = None) -> None:
        self._descriptors: dict[str, PillarDescriptor] = {}
        self._modules: dict[str, PillarModule] = {}
        self._routers: dict[str, APIRouter] = {}
        self._enabled_ids = enabled_ids or _enabled_ids_from_settings

    # -- registration -------------------------------------------------------
    def register_descriptor(self, descriptor: PillarDescriptor) -> None:
        if descriptor.pillar_id in self._descriptors:
            raise ValueError(f"pillar {descriptor.pillar_id!r} is already registered")
        self._descriptors[descriptor.pillar_id] = descriptor

    def register_module(self, module: PillarModule, router: Optional[APIRouter] = None) -> None:
        """Attach an implementation (and optionally its router) to a declared pillar."""
        if not isinstance(module, PillarModule):
            raise TypeError(
                f"{type(module).__name__} does not satisfy the PillarModule protocol"
            )
        if module.pillar_id not in self._descriptors:
            raise ValueError(
                f"pillar {module.pillar_id!r} has no descriptor — declare it before implementing it"
            )
        self._modules[module.pillar_id] = module
        if router is not None:
            self._routers[module.pillar_id] = router
        log.info("Pillar module registered: %s", module.pillar_id)

    # -- queries ------------------------------------------------------------
    def get(self, pillar_id: str) -> Optional[PillarDescriptor]:
        listed = {d.pillar_id: d for d in self.list()}
        return listed.get(pillar_id)

    def is_enabled(self, pillar_id: str) -> bool:
        d = self.get(pillar_id)
        return bool(d and d.enabled)

    def list(self) -> list[PillarDescriptor]:
        """Descriptors with derived state. `enabled` requires implemented AND
        opted in via settings; `status` is "live" only when enabled."""
        enabled_ids = self._enabled_ids()
        out: list[PillarDescriptor] = []
        for d in self._descriptors.values():
            implemented = d.implemented or d.pillar_id in self._modules
            enabled = implemented and d.pillar_id in enabled_ids
            out.append(
                d.model_copy(
                    update={
                        "implemented": implemented,
                        "enabled": enabled,
                        "status": "live" if enabled else "registered",
                    }
                )
            )
        return out

    # -- mounting -----------------------------------------------------------
    def mount_all(self, parent: APIRouter, limiter: InMemoryRateLimiter,
                  client_ip: Callable[[Request], str]) -> None:
        """Mount every implemented pillar's router under /api/pillars/{id}.

        Each mounted route inherits (a) the enabled check — a merged but
        not-yet-enabled pillar answers 503, never leaks partial output — and
        (b) the shared per-IP throttle, same mechanism and 429 shape as
        /api/analyse-catch.
        """
        for pillar_id, pillar_router in self._routers.items():
            parent.include_router(
                pillar_router,
                prefix=f"/api/pillars/{pillar_id}",
                tags=[f"pillar:{pillar_id}"],
                dependencies=[Depends(self._guard(pillar_id, limiter, client_ip))],
            )

    def _guard(self, pillar_id: str, limiter: InMemoryRateLimiter,
               client_ip: Callable[[Request], str]) -> Callable:
        def _check(request: Request) -> None:
            if not self.is_enabled(pillar_id):
                raise HTTPException(
                    503,
                    f"Pillar '{pillar_id}' is registered but not enabled on this deployment.",
                )
            if not limiter.allow(client_ip(request)):
                raise HTTPException(
                    429,
                    "Too many pillar requests from this address — please wait a minute and try again.",
                    headers={"Retry-After": "60"},
                )
        return _check


# ---------------------------------------------------------------------------
# The six national pillars — government naming verbatim.
# ---------------------------------------------------------------------------

def register_default_pillars(registry: PillarRegistry) -> None:
    registry.register_descriptor(PillarDescriptor(
        pillar_id="fisheries",
        pillar_name="Sustainable Fisheries & Aquaculture",
        implemented=True,
        owner="team (shipped)",
        # DESCRIPTIONS ARE RENDERED ON /pillars AND /pillars/:id. Write them for
        # a fisher or an officer: what the pillar does, not how it is wired. No
        # task references, no module layout, no file paths — that belongs in code
        # comments like this one, where it is useful and out of sight.
        description=(
            "Record a catch from a photo, check it against the GN 167/2016 size "
            "and season rules, log it to a tamper-evident record, and prepare a "
            "declaration."
        ),
        sources=[
            SourceDescriptor(name="Open-Meteo Marine", url="https://marine-api.open-meteo.com/v1/marine",
                             description="Sea state and forecast for Mauritian waters.", status="verified"),
            SourceDescriptor(name="Mauritius fisheries size and season rules", url=None,
                             description="Held on the device; works with no signal.", status="verified"),
        ],
        endpoints=["/api/analyse-catch", "/api/catches", "/api/ledger", "/api/verify/{id}", "/api/declarations"],
    ))
    registry.register_descriptor(PillarDescriptor(
        pillar_id="transport",
        pillar_name="Marine Transport & Trade",
        owner="Yadhav (WS1)",
        # Keeps both honesty facts, drops the implementation words: the bands are
        # fixed rather than guessed, and vessel tracking is genuinely unavailable
        # here (no terrestrial AIS receiver reaches Mauritius) rather than omitted.
        description=("Live sea state on the Port Louis approach, sorted into good, moderate "
                     "and poor transit windows against fixed limits. Vessel tracking is not "
                     "included: no public receiver covers Mauritius."),
        sources=list(transport_pillar.sources()),
        # /approach first: it is what the UI leads with, and the only one of the
        # two that returns genuinely live data.
        endpoints=["/api/pillars/transport/approach", "/api/pillars/transport/arrivals"],
    ))
    registry.register_descriptor(PillarDescriptor(
        pillar_id="tourism",
        pillar_name="Sustainable Ocean Tourism",
        owner="Dhanesh (WS2)",
        description="Beach and lagoon conditions for tour operators: swimming, snorkelling and small-boat suitability, site by site.",
        sources=[SourceDescriptor(name="Open-Meteo Marine", url="https://marine-api.open-meteo.com/v1/marine",
                                  description="Sea state and forecast for Mauritian waters.", status="verified")],
    ))
    registry.register_descriptor(PillarDescriptor(
        pillar_id="energy",
        pillar_name="Ocean-Based Renewable Energy",
        owner="Dhanesh (WS2)",
        description="Wind and wave resource at candidate offshore sites, for judging where marine energy is worth studying.",
        sources=[SourceDescriptor(name="Open-Meteo Marine", url="https://marine-api.open-meteo.com/v1/marine",
                                  description="Sea state and forecast for Mauritian waters.", status="verified")],
    ))
    registry.register_descriptor(PillarDescriptor(
        pillar_id="finance",
        pillar_name="Blue Finance",
        owner="Shirish (WS3)",
        description="Checks a blue-bond or ESG document against blue-finance criteria. Findings are advisory, and nothing is changed or filed.",
        sources=[SourceDescriptor(name="Uploaded documents", url=None,
                                  description="Only the document you upload. Nothing is fetched from outside.", status="none")],
    ))
    registry.register_descriptor(PillarDescriptor(
        pillar_id="biotech",
        pillar_name="Marine Biotechnology",
        owner="Shirish (WS3, stretch)",
        description="Cataloguing assistance for marine research literature and samples.",
        sources=[SourceDescriptor(name="Uploaded documents", url=None,
                                  description="Only the document you upload. Nothing is fetched from outside.", status="none")],
    ))

    # Implementations. Declaring a descriptor above and attaching a module here
    # are separate acts on purpose: a pillar is only "live" when it is both
    # implemented AND named in PILLARS_ENABLED, so landing this code does not
    # by itself expose the route (Task 4a §4).
    registry.register_module(transport_pillar, router=transport_router)


pillar_registry = PillarRegistry()
register_default_pillars(pillar_registry)
