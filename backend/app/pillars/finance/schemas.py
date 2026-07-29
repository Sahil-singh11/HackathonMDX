"""Blue Finance result shapes.

No shared cross-pillar "agent finding" shape exists yet — backend/app/agent/**
was never built (confirmed at the Task 6.0 gate: only the tool allow-list and
the 429 interceptor landed from that workstream). CriteriaFinding is defined
here, scoped to this pillar; if the agent workstream resumes, this shape is a
reasonable candidate to promote into a shared module rather than duplicate.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.pillars.base import PillarResult

CriteriaStatus = Literal["met", "unmet", "indeterminate"]


class ExtractedField(BaseModel):
    """One field the model proposed, with code-verified support.

    `supported=False` means either the model gave no page/span, or the code
    could not locate that span on that page of the actual extracted text —
    in both cases the field counts as NOT demonstrated, never as a silent
    blank standing in for "unmet".
    """

    field: str = Field(min_length=1)
    value: Optional[str] = None
    page: Optional[int] = None
    span: Optional[str] = None
    supported: bool = False
    unsupported_reason: str = ""


class CriteriaFinding(BaseModel):
    """One criterion's computed status. Never a verdict on the bond as a whole."""

    criterion_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: CriteriaStatus
    evidence: list[ExtractedField] = Field(default_factory=list)
    note: str = Field(min_length=1)
    advisory_only: bool = False


class BlueFinanceResult(PillarResult):
    """Task 4a: subclasses PillarResult, so `provenance` stays mandatory."""

    document_label: str = Field(min_length=1)
    fields: list[ExtractedField] = Field(default_factory=list)
    findings: list[CriteriaFinding] = Field(default_factory=list)
    overall_note: str = Field(
        min_length=1,
        description="Never a pass/fail verdict on the bond — states what was checked and what was not.",
    )
