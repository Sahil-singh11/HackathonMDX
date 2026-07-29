"""Allow-listed function registry for Gemma native function calling.

Safety properties:
- EXPLICIT function map (no eval/exec/globals dispatch, no arbitrary URLs/shell).
- Pydantic argument validation before any handler runs; invalid args fail safely.
- Unknown function names fail safely with status "unknown_function".
- Traces record argument NAMES only (values may contain user data) and never
  precise coordinates.
- Network-touching handlers carry their own timeouts (httpx) and bounded retries.
"""
from __future__ import annotations

import json
import time
from typing import Callable

from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session, select

from app.core.limitations import MARINE_DISCLAIMER, RULE_VERIFY_NOTICE
from app.models.entities import CatchRecord, SyncQueueItem, ToolTrace
from app.schemas.analysis import FunctionTraceEntry
from app.services.declarations import service as declarations
from app.services.fisheries_rules import demo_date, engine as rules_engine
from app.services.marine.client import get_marine_conditions
from app.services.species.retrieval import candidates_for, get_species, public_candidate


class ToolContext:
    def __init__(self, session: Session, language: str = "en", allow_network: bool = True, analysis_id: str | None = None):
        self.session = session
        self.language = language
        self.allow_network = allow_network
        self.analysis_id = analysis_id


# ---------- argument models ----------

class MarineArgs(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class CandidatesArgs(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class SpeciesDetailsArgs(BaseModel):
    species_id: str = Field(max_length=64)


class RecentCatchesArgs(BaseModel):
    limit: int = Field(default=5, ge=1, le=50)


class RecordCatchArgs(BaseModel):
    species_id: str = Field(max_length=64)
    measured_length_cm: float | None = Field(default=None, gt=0, lt=500)
    count: int = Field(default=1, ge=1, le=1000)
    capture_date: str | None = None
    fishing_area: str = Field(default="", max_length=120)


class RuleCheckArgs(BaseModel):
    species_id: str = Field(max_length=64)
    measured_length_cm: float | None = Field(default=None, gt=0, lt=500)
    capture_date: str | None = None


class PrepareDeclarationArgs(BaseModel):
    fisher_name: str = Field(default="", max_length=120)
    fishing_area: str = Field(default="", max_length=120)
    period_start: str
    period_end: str


class SubmitMockArgs(BaseModel):
    declaration_id: str = Field(max_length=64)


class QueueSyncArgs(BaseModel):
    kind: str = Field(default="catch_record", max_length=40)
    payload: dict = Field(default_factory=dict)


class BetterPhotoArgs(BaseModel):
    reason: str = Field(default="", max_length=300)


class EmptyArgs(BaseModel):
    pass


class TranslateArgs(BaseModel):
    message_key: str = Field(max_length=60)
    language: str = Field(default="mfe", pattern="^(en|mfe)$")


# ---------- handlers ----------

def _h_marine(args: MarineArgs, ctx: ToolContext) -> dict:
    return get_marine_conditions(ctx.session, args.latitude, args.longitude, allow_network=ctx.allow_network)


def _h_candidates(args: CandidatesArgs, ctx: ToolContext) -> dict:
    return {"candidates": [public_candidate(s) for s in candidates_for(args.note)]}


def _h_species_details(args: SpeciesDetailsArgs, ctx: ToolContext) -> dict:
    sp = get_species(args.species_id)
    if not sp:
        return {"error": "species_not_found"}
    return public_candidate(sp)


def _h_recent_catches(args: RecentCatchesArgs, ctx: ToolContext) -> dict:
    rows = ctx.session.exec(
        select(CatchRecord).order_by(CatchRecord.created_at.desc()).limit(args.limit)  # type: ignore[union-attr]
    ).all()
    return {"catches": [
        {"species_id": r.species_id, "count": r.count, "capture_date": r.capture_date,
         "measured_length_cm": r.measured_length_cm, "legal_status": r.legal_status}
        for r in rows
    ]}


def _h_record_catch(args: RecordCatchArgs, ctx: ToolContext) -> dict:
    cur, _sim = demo_date.get_current_date(ctx.session)
    rec = CatchRecord(
        species_id=args.species_id, measured_length_cm=args.measured_length_cm,
        count=args.count, capture_date=args.capture_date or cur.isoformat(),
        fishing_area=args.fishing_area, legal_status="unknown",
        legal_note="Recorded via assistant; deterministic rule check requires the confirmation flow.",
    )
    ctx.session.add(rec)
    ctx.session.commit()
    ctx.session.refresh(rec)
    return {"catch_record_id": rec.id, "legal_status": "unknown"}


def _h_rule_check(args: RuleCheckArgs, ctx: ToolContext) -> dict:
    from datetime import date
    cur, simulated = demo_date.get_current_date(ctx.session)
    d = date.fromisoformat(args.capture_date) if args.capture_date else cur
    check = rules_engine.check_confirmed_catch(args.species_id, args.measured_length_cm, d)
    return {"legal_check": check.model_dump(), "date_used": d.isoformat(), "date_simulated": simulated,
            "notice": RULE_VERIFY_NOTICE}


def _h_prepare_declaration(args: PrepareDeclarationArgs, ctx: ToolContext) -> dict:
    decl = declarations.prepare(ctx.session, args.fisher_name, args.fishing_area, args.period_start, args.period_end)
    return {"declaration_id": decl.id, "status": decl.status, "label": declarations.MOCK_LABEL}


def _h_submit_mock(args: SubmitMockArgs, ctx: ToolContext) -> dict:
    decl = declarations.mock_submit(ctx.session, args.declaration_id)
    if not decl:
        return {"error": "declaration_not_found"}
    return {"declaration_id": decl.id, "status": decl.status,
            "mock_receipt_id": decl.mock_receipt_id, "label": declarations.MOCK_LABEL}


def _h_queue_sync(args: QueueSyncArgs, ctx: ToolContext) -> dict:
    item = SyncQueueItem(kind=args.kind, payload_json=json.dumps(args.payload)[:4000])
    ctx.session.add(item)
    ctx.session.commit()
    ctx.session.refresh(item)
    return {"queue_item_id": item.id, "status": item.status}


def _h_better_photo(args: BetterPhotoArgs, ctx: ToolContext) -> dict:
    return {"guidance": [
        "Keep the whole catch visible in the frame",
        "Use adequate light and avoid glare",
        "Place a ruler next to the catch when size matters",
        "Avoid faces and private information in the photo",
    ], "reason": args.reason}


def _h_demo_date(args: EmptyArgs, ctx: ToolContext) -> dict:
    d, simulated = demo_date.get_current_date(ctx.session)
    return {"date": d.isoformat(), "simulated": simulated}


_STATIC_MESSAGES = {
    "marine_disclaimer": {"en": MARINE_DISCLAIMER,
                          "mfe": "Previzion lamer zis pou lenformasion; kapav manke presizion pre ar lakot. "
                                 "Verifie avek bilten ofisiel avan sorti lor lamer."},
    "rule_verify": {"en": RULE_VERIFY_NOTICE,
                    "mfe": "Verifie avek dernie lavi ofisiel lapes avan pran desizion."},
    "confirmation_needed": {"en": "Please confirm or correct the suggested species before recording.",
                            "mfe": "Silvouple konfirm ouswa koriz lespes sizere avan anrezistre."},
}


def _h_translate(args: TranslateArgs, ctx: ToolContext) -> dict:
    entry = _STATIC_MESSAGES.get(args.message_key)
    if not entry:
        return {"error": "unknown_message_key", "available": sorted(_STATIC_MESSAGES)}
    return {"message_key": args.message_key, "language": args.language, "text": entry[args.language]}


# ---------- explicit allow-list map ----------

REGISTRY: dict[str, tuple[type[BaseModel], Callable]] = {
    "get_marine_conditions": (MarineArgs, _h_marine),
    "get_species_candidates": (CandidatesArgs, _h_candidates),
    "get_species_details": (SpeciesDetailsArgs, _h_species_details),
    "get_recent_catches": (RecentCatchesArgs, _h_recent_catches),
    "record_catch": (RecordCatchArgs, _h_record_catch),
    "check_confirmed_catch_rule": (RuleCheckArgs, _h_rule_check),
    "prepare_catch_declaration": (PrepareDeclarationArgs, _h_prepare_declaration),
    "submit_mock_declaration": (SubmitMockArgs, _h_submit_mock),
    "queue_for_offline_sync": (QueueSyncArgs, _h_queue_sync),
    "request_better_photo": (BetterPhotoArgs, _h_better_photo),
    "get_current_demo_date": (EmptyArgs, _h_demo_date),
    "translate_safe_static_message": (TranslateArgs, _h_translate),
}


def execute(name: str, raw_args: dict, ctx: ToolContext) -> tuple[dict, FunctionTraceEntry]:
    """Validate and run an allow-listed function. Never raises to the caller.

    A name that is registered but was never DECLARED to the model is rejected
    identically to a genuinely unknown one: from the model's point of view it
    was never told the function exists, so it must not be reachable either.
    This is the runtime half of the allow-list; the test-time half is
    test_tool_allowlist.py's identity assertion.
    """
    start = time.monotonic()
    entry = REGISTRY.get(name)
    if entry is None or name not in DECLARED:
        trace = FunctionTraceEntry(function=name, argument_names=[], result_status="unknown_function",
                                   duration_ms=0, final_action="rejected")
        _persist_trace(ctx, trace)
        return {"error": "unknown_function"}, trace

    model_cls, handler = entry
    try:
        args = model_cls(**(raw_args or {}))
    except ValidationError as e:
        trace = FunctionTraceEntry(function=name, argument_names=sorted((raw_args or {}).keys()),
                                   result_status="invalid_arguments", duration_ms=0, final_action="rejected")
        _persist_trace(ctx, trace)
        return {"error": "invalid_arguments", "detail_count": e.error_count()}, trace

    try:
        result = handler(args, ctx)
        status = "error" if isinstance(result, dict) and result.get("error") else "ok"
    except Exception:  # noqa: BLE001 — tools must fail safely
        result = {"error": "tool_execution_failed"}
        status = "error"
    duration_ms = int((time.monotonic() - start) * 1000)
    trace = FunctionTraceEntry(function=name, argument_names=sorted(args.model_dump(exclude_none=True).keys()),
                               result_status=status, duration_ms=duration_ms, final_action="executed")
    _persist_trace(ctx, trace)
    return result, trace


def _persist_trace(ctx: ToolContext, trace: FunctionTraceEntry) -> None:
    try:
        ctx.session.add(ToolTrace(
            analysis_id=ctx.analysis_id, function_name=trace.function,
            argument_names=",".join(trace.argument_names), result_status=trace.result_status,
            duration_ms=trace.duration_ms, final_action=trace.final_action,
        ))
        ctx.session.commit()
    except Exception:  # noqa: BLE001 — tracing must never break the request
        ctx.session.rollback()


def gemma_function_declarations() -> list[dict]:
    """JSON-schema declarations for the google-genai SDK (subset offered to the model)."""
    def decl(name: str, description: str, params: dict, required: list[str] | None = None) -> dict:
        return {"name": name, "description": description,
                "parameters": {"type": "object", "properties": params, "required": required or []}}

    return [
        decl("get_marine_conditions", "Get current marine conditions (waves, swell, sea temperature) near a Mauritius location.",
             {"latitude": {"type": "number"}, "longitude": {"type": "number"}}),
        decl("get_species_candidates", "Get the allowed candidate species shortlist for identification.",
             {"note": {"type": "string"}}),
        decl("get_species_details", "Get details for one species in the catalogue.",
             {"species_id": {"type": "string"}}, ["species_id"]),
        decl("get_recent_catches", "List the fisher's recent catch records.",
             {"limit": {"type": "integer"}}),
        decl("record_catch", "Record a catch the fisher has ALREADY confirmed. Only call this after the fisher "
                             "confirmed the species; measured_length_cm must come from a real measurement, never "
                             "from an image estimate.",
             {"species_id": {"type": "string"}, "measured_length_cm": {"type": "number"},
              "count": {"type": "integer"}, "capture_date": {"type": "string"},
              "fishing_area": {"type": "string"}},
             ["species_id"]),
        decl("check_confirmed_catch_rule", "Deterministically check the recorded fisheries rule for a CONFIRMED species and measured length.",
             {"species_id": {"type": "string"}, "measured_length_cm": {"type": "number"}, "capture_date": {"type": "string"}},
             ["species_id"]),
        decl("prepare_catch_declaration", "Draft a declaration from the fisher's confirmed catches in a date range. "
                                          "Demonstration only — this is never a real government submission.",
             {"fisher_name": {"type": "string"}, "fishing_area": {"type": "string"},
              "period_start": {"type": "string"}, "period_end": {"type": "string"}},
             ["period_start", "period_end"]),
        decl("submit_mock_declaration", "Submit a previously prepared declaration to the MOCK demonstration "
                                        "endpoint. This never contacts a real government system.",
             {"declaration_id": {"type": "string"}}, ["declaration_id"]),
        decl("queue_for_offline_sync", "Queue an action (e.g. a catch record) for later sync when connectivity "
                                       "returns, instead of losing it.",
             {"kind": {"type": "string"}, "payload": {"type": "object"}}),
        decl("request_better_photo", "Ask the fisher to retake the photo with guidance.",
             {"reason": {"type": "string"}}),
        decl("get_current_demo_date", "Get the current (possibly simulated) app date.", {}),
        decl("translate_safe_static_message", "Fetch an approved static safety message in en or mfe.",
             {"message_key": {"type": "string"}, "language": {"type": "string"}}, ["message_key"]),
    ]


# Every name REGISTRY can execute must appear here too. execute() enforces this
# at runtime (defence in depth); test_tool_allowlist.py enforces it at test time
# so the two lists can never silently drift apart again.
DECLARED: frozenset[str] = frozenset(d["name"] for d in gemma_function_declarations())
