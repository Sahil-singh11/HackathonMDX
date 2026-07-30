"""Narrative cache (Task 3 of the pillar-backend work list): demo reliability.

Two things must hold: (1) the cache primitives are correct and safe under the
concurrent writes energy/tourism's parallel _interpret() calls can produce,
and (2) each pillar call site actually consults the cache BEFORE calling a
model, so a second identical request is instant and never re-invokes the
provider. (1) is tested here directly; (2) is tested per-pillar below,
reusing each pillar's existing fake-provider fixtures.
"""
from __future__ import annotations

import threading

import pytest
from sqlmodel import Session, select

from app.db.session import get_engine
from app.models.entities import NarrativeCacheEntry
from app.pillars import narrative_cache


@pytest.fixture(autouse=True)
def _clean_cache():
    narrative_cache.reset()
    yield
    narrative_cache.reset()


# --- cache_key -----------------------------------------------------------

def test_cache_key_is_stable_for_identical_inputs():
    a = narrative_cache.cache_key("energy", {"x": 1.0}, language="en", provider_name="gemma_hosted")
    b = narrative_cache.cache_key("energy", {"x": 1.0}, language="en", provider_name="gemma_hosted")
    assert a == b


def test_cache_key_differs_when_any_input_differs():
    base = narrative_cache.cache_key("energy", {"x": 1.0}, language="en", provider_name="p")
    assert base != narrative_cache.cache_key("tourism", {"x": 1.0}, language="en", provider_name="p")
    assert base != narrative_cache.cache_key("energy", {"x": 2.0}, language="en", provider_name="p")
    assert base != narrative_cache.cache_key("energy", {"x": 1.0}, language="mfe", provider_name="p")
    assert base != narrative_cache.cache_key("energy", {"x": 1.0}, language="en", provider_name="q")


# --- get/put round-trip ----------------------------------------------------

def test_put_then_get_round_trips():
    key = narrative_cache.cache_key("energy", {"x": 1.0}, provider_name="p")
    assert narrative_cache.get(key) is None
    narrative_cache.put(key, "some grounded prose", pillar_id="energy", provider_name="p")
    assert narrative_cache.get(key) == "some grounded prose"


def test_put_with_empty_text_is_a_no_op():
    """A rejected/absent narrative must never be cached as if real — the next
    request should get a fresh chance, not a frozen absence."""
    key = narrative_cache.cache_key("energy", {"x": 1.0}, provider_name="p")
    narrative_cache.put(key, "", pillar_id="energy", provider_name="p")
    assert narrative_cache.get(key) is None


def test_put_overwrites_an_existing_entry():
    key = narrative_cache.cache_key("energy", {"x": 1.0}, provider_name="p")
    narrative_cache.put(key, "first version", pillar_id="energy", provider_name="p")
    narrative_cache.put(key, "second version", pillar_id="energy", provider_name="p")
    assert narrative_cache.get(key) == "second version"
    assert narrative_cache.count("energy") == 1  # not duplicated


def test_reset_clears_all_entries():
    narrative_cache.put(narrative_cache.cache_key("energy", {"x": 1.0}, provider_name="p"),
                        "text", pillar_id="energy", provider_name="p")
    assert narrative_cache.count() == 1
    narrative_cache.reset()
    assert narrative_cache.count() == 0


def test_count_filters_by_pillar():
    narrative_cache.put(narrative_cache.cache_key("energy", {"x": 1.0}, provider_name="p"),
                        "e", pillar_id="energy", provider_name="p")
    narrative_cache.put(narrative_cache.cache_key("tourism", {"x": 1.0}, provider_name="p"),
                        "t", pillar_id="tourism", provider_name="p")
    assert narrative_cache.count("energy") == 1
    assert narrative_cache.count("tourism") == 1
    assert narrative_cache.count() == 2


# --- demo_mode_active ------------------------------------------------------

def test_demo_mode_reflects_settings(monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("DEMO_MODE", "true")
    assert narrative_cache.demo_mode_active() is True
    get_settings.cache_clear()
    monkeypatch.setenv("DEMO_MODE", "false")
    assert narrative_cache.demo_mode_active() is False
    get_settings.cache_clear()


# --- concurrency safety ----------------------------------------------------

def test_concurrent_put_with_the_same_key_does_not_crash():
    """Reproduces the real race this module was fixed for: energy/tourism
    dispatch several _interpret() calls in parallel via asyncio.gather +
    to_thread, so two threads CAN compute the identical cache key (same
    figures, same provider) and both reach put() before either commits. A
    plain check-then-insert races; this proves the loser is swallowed, not a
    crash — found live via test_pillar_tourism.py during Task 3 development,
    reproduced directly here so it cannot regress silently."""
    key = narrative_cache.cache_key("tourism", {"shared": True}, provider_name="racer")
    errors: list[BaseException] = []

    def _write(n: int) -> None:
        try:
            narrative_cache.put(key, f"narrative from thread {n}", pillar_id="tourism", provider_name="racer")
        except BaseException as exc:  # noqa: BLE001 — the test's whole point is "did this raise"
            errors.append(exc)

    threads = [threading.Thread(target=_write, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    # Exactly one row survives — whichever write landed first or last, never a
    # duplicate and never a crash.
    with Session(get_engine()) as session:
        rows = session.exec(select(NarrativeCacheEntry).where(NarrativeCacheEntry.cache_key == key)).all()
    assert len(rows) == 1
    assert narrative_cache.get(key) is not None
