"""Pillar module contract — the extension point for the blue-economy pillars.

Interface frozen at Task 4a (sync point S4), mirroring the Task 1a provider
freeze: Workstreams 2 and 3 build their pillar modules against this file and
`registry.py` only. Changing a signature after S4 requires a decision-log
entry (docs/DECISION_LOG.md).

Boundary rule (tested in tests/test_pillar_contract.py): nothing under
app/pillars imports a model SDK, an HTTP model client, or a provider module
directly. Every model call goes through `app.inference.base` /
`app.inference.registry`. The test walks this package's imports and fails
the suite on any violation, so the rule cannot erode silently.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.pillars.provenance import DataKind, DataProvenance


class SourceDescriptor(BaseModel):
    """One declared external data source for a pillar.

    `status` is an honesty field: a source stays "candidate" until its owner
    has seen a real message/response from it during build ("verified").
    Descriptor-only pillars may declare "none" while unassigned.
    """

    name: str = Field(min_length=1)
    url: Optional[str] = None
    description: str = ""
    status: Literal["verified", "candidate", "none"] = "candidate"


class RawBundle(BaseModel):
    """What fetch() hands to analyse().

    Carries the payload plus everything analyse() needs to build the
    mandatory DataProvenance without guessing: the source it actually came
    from, when, its data_kind, and the coverage note. If fetch() degraded
    (live -> cached -> sample), the bundle says so — analyse() never
    re-labels data as fresher than it is.
    """

    pillar_id: str = Field(min_length=1)
    source: SourceDescriptor
    retrieved_at: datetime
    data_kind: DataKind
    coverage_note: str = Field(min_length=1)
    payload: Any = None


class PillarResult(BaseModel):
    """Base class for every pillar's result_schema.

    `provenance` is a required field HERE, on the base — no subclass can be
    instantiated without it, which is the structural guarantee Task 4a
    promises Workstream 3's enforcement tests.
    """

    pillar_id: str = Field(min_length=1)
    generated_at: datetime
    provenance: DataProvenance


@runtime_checkable
class PillarModule(Protocol):
    """One blue-economy pillar implementation.

    - `pillar_id` is the stable slug used in routes and settings.
    - `pillar_name` is the government's own pillar naming, verbatim.
    - `sources()` declares the external data sources, honestly statused.
    - `fetch()` retrieves (and may cache or degrade — the RawBundle records
      which of those happened).
    - `analyse()` is the model step. It routes through app.inference.base /
      app.inference.registry ONLY, and returns a `result_schema` instance,
      which subclasses PillarResult and therefore carries provenance.
    """

    pillar_id: str
    pillar_name: str
    result_schema: type[PillarResult]

    def sources(self) -> list[SourceDescriptor]:
        ...

    async def fetch(self, params: dict) -> RawBundle:
        ...

    async def analyse(self, bundle: RawBundle) -> PillarResult:
        ...
