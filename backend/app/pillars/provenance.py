"""DataProvenance — the mandatory honesty block on every pillar result.

Defined at Task 4a (sync point S4). Every PillarResult carries exactly one of
these, non-nullable: a result that cannot say where its data came from, how
fresh it is, which inference provider reasoned over it and what the data does
NOT cover is invalid by construction. The min_length constraints are the
enforcement — an empty coverage note or a blank provider is a ValidationError,
not a style problem. Workstream 3 adds cross-pillar enforcement tests on top;
this module makes omission structurally impossible at the model layer.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# "live"      — fetched from the declared external source during this request window
# "cached"    — served from an earlier live fetch (staleness visible via retrieved_at)
# "sample"    — a committed capture, labelled as such on every surface that shows it
# "synthetic" — generated fixture data; never presented as an observation
DataKind = Literal["live", "cached", "sample", "synthetic"]


class DataProvenance(BaseModel):
    """Where a pillar result's data came from — and what it does not cover."""

    source_name: str = Field(min_length=1)
    source_url: Optional[str] = None
    retrieved_at: datetime
    data_kind: DataKind
    model_provider: str = Field(
        min_length=1,
        description=(
            "Inference provider that served the model step, as reported by the "
            "inference registry (e.g. gemma_hosted, mock). Mirrors the "
            "X-Inference-Provider honesty mechanism from Task 1a."
        ),
    )
    coverage_note: str = Field(
        min_length=1,
        description="What this data does NOT cover. Mandatory and never empty.",
    )
