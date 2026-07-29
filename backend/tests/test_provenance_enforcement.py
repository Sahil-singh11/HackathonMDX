"""Task 6a — provenance enforcement.

A structural guarantee, not a promise. Two failure modes are guarded here:

1. A pillar module that produces a result without genuine provenance — caught
   by walking every module actually attached to the live registry and
   validating every DataProvenance field for real, not just checking the type
   exists (test_pillar_contract.py already proves the shape is mandatory;
   this proves the CONTENT is honest).
2. A pillar that silently widens the executable-tool surface without
   declaring it to the model — caught by proving the existing allow-list
   identity test (test_tool_allowlist.py) actually trips on that exact
   scenario, not just trusting it by inspection.

As of this commit, zero PillarModule instances are attached to the real
registry (fisheries is deliberately routes-only, per Task 4a §5; the other
five are descriptor-only). So test_pillar_provenance_contract's real
enforcement branch does not fire on anything YET — but it is written to
activate automatically, with no code change here, the moment any pillar
attaches a module. The "not implemented" branch asserts the registry's own
state is coherent instead of skipping, so this file can never pass vacuously.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import get_args

import pytest
from pydantic import ValidationError

from sqlmodel import Session

from app.db.session import get_engine
from app.inference.registry import CANONICAL
from app.pillars.base import PillarResult
from app.pillars.provenance import DataKind, DataProvenance
from app.pillars.registry import pillar_registry

# Generic, low-effort placeholders a careless implementation might leave in —
# not exhaustive, just enough to catch copy-pasted boilerplate.
BOILERPLATE_COVERAGE_NOTES = {"", "n/a", "none", "todo", "tbd", "coverage note"}

ALL_PILLAR_IDS = [d.pillar_id for d in pillar_registry.list()]

# Task 4a §5: fisheries is deliberately NOT refactored into a PillarModule —
# it stays on its existing production routes (analyse-catch, ledger,
# declarations), which already carry their own honesty mechanisms (mock/
# fallback disclosure, per-request provider recording, ledger scope notes),
# tested in test_api_flow.py / test_ledger.py. It is the one documented
# exception to "no module attached => not implemented" below.
ROUTES_ONLY_PILLARS = {"fisheries"}


def _run(coro):
    return asyncio.run(coro)


def _fresh_provenance(**overrides) -> DataProvenance:
    base = dict(source_name="fixture", source_url=None, retrieved_at=datetime.now(timezone.utc),
                data_kind="sample", model_provider="mock", coverage_note="test fixture")
    base.update(overrides)
    return DataProvenance(**base)


# -- 1. every attached pillar produces real provenance; every unattached one
#       reports itself honestly rather than being silently skipped ----------

@pytest.mark.parametrize("pillar_id", ALL_PILLAR_IDS)
def test_pillar_provenance_contract(pillar_id):
    descriptor = pillar_registry.get(pillar_id)
    module = pillar_registry._modules.get(pillar_id)  # same private-access pattern as test_pillar_contract.py

    if module is None:
        if pillar_id in ROUTES_ONLY_PILLARS:
            # Documented exception: implemented+enabled without a module is
            # correct here. Confirm the registry's bookkeeping matches what
            # it claims rather than skipping this pillar silently.
            assert descriptor.implemented is True
            assert descriptor.enabled is True
            assert descriptor.status == "live"
            return
        # Not implemented: assert the registry SAYS so, rather than letting
        # this test node quietly do nothing. If a module were attached
        # without updating implemented/enabled bookkeeping, this fails.
        assert descriptor.implemented is False, (
            f"{pillar_id}: registry reports implemented=True but no module is attached to "
            "pillar_registry._modules, and it is not in ROUTES_ONLY_PILLARS — the enforcement "
            "branch below was never exercised for it."
        )
        assert descriptor.enabled is False
        return

    # A generic params baseline, not an empty dict: real finding from adding
    # tourism/energy to the registry — their fetch() requires params["session"]
    # (documented in their own docstrings), which an empty dict can't supply.
    # session/allow_network are extra, unused keys for pillars that don't need
    # them (finance, transport) — every fetch() observed so far tolerates
    # unrecognised params rather than requiring an exact key set.
    with Session(get_engine()) as session:
        bundle = _run(module.fetch(params={"session": session, "allow_network": False}))
        result = _run(module.analyse(bundle))

    assert isinstance(result, PillarResult), f"{pillar_id}: analyse() did not return a PillarResult"
    prov = result.provenance
    assert isinstance(prov, DataProvenance)

    assert prov.source_name.strip(), f"{pillar_id}: empty source_name"
    assert prov.data_kind in get_args(DataKind), f"{pillar_id}: invalid data_kind {prov.data_kind!r}"

    assert prov.model_provider.strip(), f"{pillar_id}: empty model_provider"
    assert prov.model_provider in (*CANONICAL, "mock"), (
        f"{pillar_id}: model_provider {prov.model_provider!r} does not match any name the "
        f"inference registry knows ({CANONICAL})"
    )

    note = prov.coverage_note.strip().lower()
    assert note, f"{pillar_id}: empty coverage_note"
    assert note not in BOILERPLATE_COVERAGE_NOTES, f"{pillar_id}: boilerplate coverage_note {prov.coverage_note!r}"

    # retrieved_at must be a real, timezone-aware timestamp — not a naive
    # datetime and not an epoch/min-date placeholder.
    assert prov.retrieved_at.tzinfo is not None, f"{pillar_id}: retrieved_at must be timezone-aware"
    assert prov.retrieved_at > datetime(2020, 1, 1, tzinfo=timezone.utc), (
        f"{pillar_id}: retrieved_at looks like a placeholder ({prov.retrieved_at!r})"
    )


# -- 2. data_kind cannot default --------------------------------------------

def test_data_kind_has_no_default_and_cannot_be_omitted():
    with pytest.raises(ValidationError):
        DataProvenance(source_name="x", source_url=None, retrieved_at=datetime.now(timezone.utc),
                      model_provider="mock", coverage_note="test")  # data_kind omitted entirely


def test_data_kind_allowed_values_are_exactly_the_documented_four():
    """Pins the Literal so a pillar cannot widen it (e.g. adding "guessed")
    without that change being visible in a diff to this test."""
    assert set(get_args(DataKind)) == {"live", "cached", "sample", "synthetic"}


def test_provenance_helper_itself_is_valid():
    # Sanity check on the fixture builder used above — if this fails, every
    # other test's baseline provenance is untrustworthy.
    prov = _fresh_provenance()
    assert prov.data_kind == "sample"


# -- 3. the tool allow-list identity test already extends to pillar tools,
#       by construction — prove the mechanism actually trips ---------------

def test_allowlist_identity_check_would_catch_a_pillar_widening_the_tool_surface():
    """test_tool_allowlist.py::test_executable_set_equals_declared_set compares
    the live REGISTRY/DECLARED sets dynamically, with no hardcoded name list —
    so it already covers any tool a future pillar registers, with no new code
    needed here. This proves that claim rather than asserting it by
    inspection: simulate a pillar adding an executable tool without declaring
    it, and confirm the identity check trips."""
    import app.tools.registry as reg

    original = dict(reg.REGISTRY)
    try:
        reg.REGISTRY["pillar_smuggled_tool"] = original["get_current_demo_date"]
        assert set(reg.REGISTRY.keys()) != reg.DECLARED, (
            "the allow-list identity check failed to notice a tool added without a declaration"
        )
    finally:
        reg.REGISTRY.clear()
        reg.REGISTRY.update(original)
    # And the real, un-tampered state still matches — the test above didn't
    # leak a mutation into the shared module dict.
    assert set(reg.REGISTRY.keys()) == reg.DECLARED
