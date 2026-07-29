"""Blue Finance pillar. Call register_finance_pillar() once, before the
pillar router is built (app.main does this at import time, ahead of
create_app()) — matches how app.pillars.registry attaches any module."""
from __future__ import annotations

from app.pillars.finance.module import BlueFinancePillar
from app.pillars.finance.routes import router as finance_router
from app.pillars.registry import pillar_registry

_registered = False


def register_finance_pillar() -> None:
    global _registered
    if _registered:
        return
    pillar_registry.register_module(BlueFinancePillar(), router=finance_router)
    _registered = True
