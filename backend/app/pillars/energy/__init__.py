"""Ocean-Based Renewable Energy pillar (Workstream 2).

`register_energy()` is called once from app.main before build_pillar_router().
Registering does NOT enable the pillar — it must also be listed in
PILLARS_ENABLED, otherwise its routes answer 503.
"""
from __future__ import annotations

import logging

from app.pillars.registry import PillarRegistry, pillar_registry

log = logging.getLogger(__name__)


def register_energy(registry: PillarRegistry | None = None) -> None:
    """Attach the energy module and its router. Idempotent."""
    from app.pillars.energy.module import energy_pillar
    from app.pillars.energy.routes import router as energy_router

    reg = registry if registry is not None else pillar_registry
    if energy_pillar.pillar_id in getattr(reg, "_modules", {}):
        return
    reg.register_module(energy_pillar, energy_router)
