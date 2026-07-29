"""Blue Finance pillar routes, mounted under /api/pillars/finance by
PillarRegistry.mount_all() (enabled-check + throttle inherited from there —
nothing here duplicates that guard)."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.pillars.finance.criteria import load_criteria
from app.pillars.finance.module import SAMPLE_DOCS, BlueFinancePillar, DocumentNotFound
from app.pillars.finance.schemas import BlueFinanceResult

router = APIRouter()
_pillar = BlueFinancePillar()


@router.get("/criteria")
def get_criteria() -> dict:
    return {"criteria": load_criteria()}


@router.get("/samples")
def list_samples() -> dict:
    return {"samples": [{"sample_id": k, "filename": v[0], "label": v[1]} for k, v in SAMPLE_DOCS.items()]}


@router.post("/analyse", response_model=BlueFinanceResult)
async def analyse(sample_id: str | None = Form(default=None),
                  document: UploadFile | None = File(default=None)) -> BlueFinanceResult:
    params: dict = {}
    if document is not None:
        params = {"pdf_bytes": await document.read(), "document_label": document.filename or "uploaded document"}
    elif sample_id is not None:
        params = {"sample_id": sample_id}

    try:
        bundle = await _pillar.fetch(params)
    except DocumentNotFound as e:
        raise HTTPException(422, str(e)) from e

    return await _pillar.analyse(bundle)
