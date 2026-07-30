"""Narrative cache: persist model prose keyed on the figures that produced it.

WHY THIS EXISTS (Task 3, demo reliability). A pillar narrative call is the
single slowest, least reliable step in any pillar response — 20-90 s against
the live hosted model, occasionally a timeout or a transient 5xx (see
transport's `narrative_note` captures). Two live requests for the SAME site
under the SAME conditions currently pay that cost twice. This cache means the
second one (and every demo rehearsal after the first) is instant and uses
REAL, previously-grounded prose — never a fabricated stand-in.

DESIGN. Keyed on (pillar, rounded input figures, language, provider) via
`cache_key()`, so two requests that would produce the same PROMPT hit the same
entry — this is a cache of "what would the model honestly say about these
exact figures", not a cache of "this exact HTTP request". Only a narrative
that already passed every existing guard (prose_or_empty, numeric_guard,
transport's narrative_is_grounded) is ever stored — see the call sites in
energy/module.py, tourism/module.py and transport/module.py, which all check
`guarded`/`grounded` before calling `put()`.

Persisted to the same on-disk SQLite database as everything else (not an
in-process dict), so a restart does not cold-start the demo — same reasoning
as MarineForecastCache, and the same reason /api/demo/reset also clears it.
"""
from __future__ import annotations

import hashlib
import json
import logging

from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.entities import NarrativeCacheEntry

log = logging.getLogger(__name__)


def cache_key(pillar_id: str, figures: dict, *, language: str = "en",
              provider_name: str = "") -> str:
    """Stable key over (pillar, figures, language, provider).

    `figures` should be the same rounded numbers the prompt actually shows the
    model (already rounded by resource.py / suitability.py / the AIS summary),
    so this is exactly the set of inputs that determine what an honest model
    response would say.
    """
    payload = json.dumps(
        {"pillar": pillar_id, "figures": figures, "language": language, "provider": provider_name},
        sort_keys=True, default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get(key: str) -> str | None:
    with Session(get_engine()) as session:
        row = session.get(NarrativeCacheEntry, key)
        return row.text if row else None


def put(key: str, text: str, *, pillar_id: str, provider_name: str) -> None:
    """No-op on empty text: a rejected/absent narrative must never be cached as
    if it were a real one — the next request should get a fresh chance, not a
    frozen absence.

    Best-effort by design, never fatal to the caller: energy and tourism
    dispatch several `_interpret()` calls in parallel (asyncio.gather +
    to_thread — Task 3's own latency fix), so concurrent writes against the
    same SQLite file are expected, not exceptional — two threads can compute
    the SAME key at once (a benign primary-key race), and SQLite's writer lock
    can occasionally make either write wait or fail outright under load. Either
    way this is a caching optimisation, not a correctness boundary: the
    narrative this call is trying to cache was ALREADY produced and grounded
    before put() was ever reached, so a failure here must never discard it —
    only the free repeat-request speedup is lost, not the result itself.
    """
    if not text:
        return
    try:
        with Session(get_engine()) as session:
            existing = session.get(NarrativeCacheEntry, key)
            if existing:
                existing.text = text
                existing.provider_name = provider_name
                session.add(existing)
            else:
                session.add(NarrativeCacheEntry(
                    cache_key=key, pillar_id=pillar_id, provider_name=provider_name, text=text,
                ))
            session.commit()
    except Exception:  # noqa: BLE001 — see docstring: caching must never be fatal
        log.info("narrative_cache: put() failed for %s (pillar=%s) — proceeding without "
                 "caching this result", key, pillar_id, exc_info=True)


def reset() -> None:
    """Called by /api/demo/reset, same contract as the rate limiters."""
    with Session(get_engine()) as session:
        for row in session.exec(select(NarrativeCacheEntry)).all():
            session.delete(row)
        session.commit()


def count(pillar_id: str | None = None) -> int:
    with Session(get_engine()) as session:
        stmt = select(NarrativeCacheEntry)
        if pillar_id:
            stmt = stmt.where(NarrativeCacheEntry.pillar_id == pillar_id)
        return len(session.exec(stmt).all())


def demo_mode_active() -> bool:
    """When true, narrative call sites must serve only from this cache and
    never call a model — see each pillar's narrative call site for the check.
    Switch on with the DEMO_MODE=true environment variable (see
    app.core.config.Settings.demo_mode). Intended for venue wifi failure: pre-
    warm the cache (see prewarm_pillar_narratives) before the session, then
    flip this on so nothing depends on connectivity for the rest of the demo.
    """
    return get_settings().demo_mode
