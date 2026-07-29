"""Provenance probe — the cheap way for an index page to show `data_kind`.

WHY THIS EXISTS. Task 5d wants /pillars to show each pillar's data_kind at a
glance. But data_kind lives on a PillarResult's provenance, and /api/pillars
returns DESCRIPTORS, which have no such field. The only way to learn a pillar's
data_kind today is to ask it for a full result — and a full result includes model
calls: measured on 2026-07-30, /api/pillars/tourism/brief and
/api/pillars/energy/resource both exceeded a 120 s timeout against hosted Gemma.
Nobody is loading an index page that costs four minutes.

A probe runs `fetch()` ONLY. That is where data_kind is decided (live vs cached
vs sample), and it is cheap because the Open-Meteo layer is cached. No inference
runs, so `model_provider` reports "not-invoked" rather than naming a provider
that did nothing — with `would_use_provider` alongside for the resolved default.
Claiming a provider served a request it never touched would break exactly the
honesty rule the provenance block exists to enforce.

CONVENTION FOR OTHER PILLAR OWNERS (Yadhav, Shirish):
    @router.get("/provenance")
    async def provenance(session=Depends(get_session)) -> dict:
        return await probe_provenance(my_pillar, {"session": session})

It is optional. A pillar without it simply returns 404, and the index renders
"does not report provenance yet" — an absence, never a guessed data_kind.
"""
from __future__ import annotations

import logging
from typing import Any

# Fully-qualified: the Task 4a boundary test allows exactly
# "app.inference.registry" and reads `from app.inference import registry` as
# importing "app.inference".
import app.inference.registry as inference_registry

log = logging.getLogger(__name__)

NOT_INVOKED = "not-invoked"


async def probe_provenance(pillar: Any, params: dict) -> dict:
    """Run a pillar's fetch() and report where the data came from.

    `params` is passed straight to fetch(), so a caller can pass
    allow_network=False the same way the tests do.
    """
    bundle = await pillar.fetch(params)

    try:
        would_use = inference_registry.resolve_name()
    except Exception:  # noqa: BLE001 — a probe must never fail on provider state
        would_use = "unknown"

    return {
        "pillar_id": bundle.pillar_id,
        "probe": True,
        "provenance": {
            "source_name": bundle.source.name,
            "source_url": bundle.source.url,
            "retrieved_at": bundle.retrieved_at.isoformat(),
            "data_kind": bundle.data_kind,
            # No inference ran. Naming a provider here would claim work that did
            # not happen; the resolved default is reported separately.
            "model_provider": NOT_INVOKED,
            "coverage_note": bundle.coverage_note,
        },
        "would_use_provider": would_use,
        "note": (
            "Data-source probe only: fetch() ran, no model inference. data_kind, "
            "source and coverage_note are real; model_provider is 'not-invoked' "
            "because nothing was generated."
        ),
    }
