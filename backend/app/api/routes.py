from __future__ import annotations

import json
import logging
import re
from datetime import date

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     Response, UploadFile)
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.limitations import (FALLBACK_DISCLOSURE, MARINE_DISCLAIMER,
                                  MOCK_DISCLOSURE, PERMANENT_LIMITATION,
                                  RULE_VERIFY_NOTICE)
from app.core.ratelimit import InMemoryRateLimiter
from app.pillars.routes import reset_limiters as _reset_pillar_limiters
from app.db.session import get_session
from app.models.entities import (AisPosition, CatchAnalysis, CatchRecord,
                                 Declaration, LedgerEntry, SyncQueueItem,
                                 ToolTrace)
from app.providers.capabilities import all_capabilities
from app.providers.dispatcher import analyse as provider_analyse
from app.schemas.analysis import (AnalyseCatchResponse, ConfirmRequest,
                                  ConfirmResponse, ConsoleError, ConsoleRequest,
                                  ConsoleResponse, LegalCheck, ProviderInfo,
                                  SpeciesSuggestion)
from app.services.declarations import service as declarations
from app.services.fisheries_rules import demo_date
from app.services.fisheries_rules.engine import check_confirmed_catch
from app.services.ledger import service as ledger
from app.services.marine.client import get_marine_conditions
from app.services.species.retrieval import (candidates_for, get_species,
                                            load_catalogue, public_candidate)
from app.services.vision.quality import assess
from app.tools.registry import ToolContext

log = logging.getLogger(__name__)
router = APIRouter()

# The public demo URL will get probed; this is a cheap, single-instance
# abuse guard, not a substitute for infra-level rate limiting.
_analyse_limiter = InMemoryRateLimiter(limit=10, window_seconds=60.0)


def _limitations(extra: list[str] | None = None) -> list[str]:
    out = [PERMANENT_LIMITATION]
    if extra:
        out.extend(extra)
    return out


def _client_ip(request: Request) -> str:
    """Best-effort client address behind a reverse proxy (e.g. Render).

    `request.client.host` is the proxy's own address unless uvicorn is
    launched with --forwarded-allow-ips for that proxy, which is not the
    case here. Falling back to X-Forwarded-For gives real per-visitor
    throttling in that deployment; a client can forge the header, but for
    a demo-abuse guard (not an auth control) that's an acceptable trade-off.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "lamer-konekte"}


@router.get("/api/config/public")
def public_config(session: Session = Depends(get_session)) -> dict:
    s = get_settings()
    d, simulated = demo_date.get_current_date(session)
    return {
        "app": "Lamer Konekte",
        "tagline": "Lapes pli konekte. Desizion pli informe.",
        "provider_mode_default": s.provider_mode,
        "hosted_configured": s.hosted_available,  # presence only — never the key
        "model": s.gemma_model if s.hosted_available else None,
        "current_date": d.isoformat(),
        "date_simulated": simulated,
        "limitation": PERMANENT_LIMITATION,
        "marine_disclaimer": MARINE_DISCLAIMER,
    }


@router.get("/api/provider/status")
def provider_status() -> dict:
    s = get_settings()
    from app.providers.local import LOCAL_MODEL_LOADED
    return {
        "hosted": {"configured": s.hosted_available, "model": s.gemma_model, "provider": "google-genai"},
        "local": {"loaded": LOCAL_MODEL_LOADED,
                  "note": "local mode appears only after a real Gemma model load"},
        "mock": {"available": True, "disclosure": MOCK_DISCLOSURE},
        "default_mode": s.provider_mode,
        # Additive: full readiness surface per provider (never includes the key).
        "capabilities": {k: v.model_dump() for k, v in all_capabilities().items()},
    }


@router.post(
    "/api/analyse-catch",
    response_model=AnalyseCatchResponse,
    summary="Analyse a catch photo and/or note (Gemma vision + text)",
    description=("Rate-limited to 10 requests/minute per client address. Species suggestions are "
                "*never* final — the response always requires human confirmation via "
                "`/api/analyses/{analysis_id}/confirm` before any legal-status rule runs."),
    responses={
        200: {
            "description": "Analysis result. Species suggestion pending human confirmation.",
            "content": {"application/json": {"example": {
                "analysis_id": "745de421-bcbd-4d6b-9550-58c1bce23a98",
                "intent": "identify_catch",
                "image_quality": {"status": "acceptable", "blur_score": 688.9, "brightness": 163.6, "warnings": []},
                "species_suggestion": {"species_id": "octopus_cyanea", "morisyen": "ourite",
                                       "english": "Day octopus", "scientific": "Octopus cyanea"},
                "visible_characteristics": ["bulbous mantle", "mottled skin", "arms with suckers"],
                "confidence_label": "high",
                "species_confirmation_required": True,
                "estimated_size_unverified_cm": None,
                "measured_size_required": True,
                "legal_check": {"status": "pending_confirmation", "rule": None, "source_id": None,
                                "verification_status": None,
                                "note": "Rule checking runs only after species confirmation with a measured length."},
                "reply": ("Is this a Day octopus (ourite)? I can see the bulbous mantle and mottled skin. "
                         "Please confirm if this is correct and provide its length in cm."),
                "reply_morisyen": ("Eski sa enn ourite? Mo trouv so mant ek so laker. Dir mwa si sa mem "
                                  "sa espis-la ek donn mwa so longer an cm."),
                "recommended_next_step": "confirm_species",
                "function_trace": [],
                "provider": {"mode": "hosted", "provider_name": "google-genai", "model": "gemma-4-26b-a4b-it",
                            "real_inference": True, "latency_ms": 27172},
                "limitations": ["Lamer Konekte provides AI-assisted catch documentation and informational "
                               "guidance. Species suggestions and regulatory checks must be confirmed "
                               "against official sources and by the fisher or an authorised officer."],
            }}},
        },
        429: {"description": "Rate limit exceeded (10 requests/minute per client address)."},
    },
)
async def analyse_catch(
    request: Request,
    response: Response,
    image: UploadFile | None = File(default=None, description="Catch photo (JPEG/PNG). Optional if a note is given."),
    note: str | None = Form(default=None,
                            description="Optional free-text note in Morisyen or English; narrows species candidates."),
    language: str = Form(default="en", description="Reply language: 'en' or 'mfe' (Morisyen)."),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    fishing_area: str = Form(default=""),
    provider_mode: str | None = Form(default=None, description="Override the default provider: hosted | local | mock."),
    session: Session = Depends(get_session),
) -> AnalyseCatchResponse:
    if not _analyse_limiter.allow(_client_ip(request)):
        raise HTTPException(429, "Too many analysis requests from this address — please wait a minute and try again.",
                            headers={"Retry-After": "60"})
    settings = get_settings()
    if language not in ("en", "mfe"):
        language = "en"
    if provider_mode not in (None, "hosted", "local", "mock"):
        raise HTTPException(422, "invalid provider_mode")
    if note:
        note = note[:500]

    analysis = CatchAnalysis(language=language)
    session.add(analysis)
    session.commit()
    session.refresh(analysis)

    resp = AnalyseCatchResponse(analysis_id=analysis.analysis_id)
    image_jpeg = None
    image_sha = None
    if image is not None:
        data = await image.read()
        # In-memory only: the upload is never written to disk, so nothing can linger.
        processed = assess(data, image.content_type, settings.upload_max_bytes)
        resp.image_quality = processed.quality
        image_jpeg, image_sha = processed.jpeg_for_api, processed.sha256
        del data
        if processed.quality.status == "invalid":
            resp.intent = "identify_catch"
            resp.recommended_next_step = "retake_photo"
            resp.reply = ("The photo cannot be analysed (" + ", ".join(processed.quality.warnings) +
                          "). Please retake it: whole catch visible, good light, no glare.")
            resp.reply_morisyen = ("Foto la pa kapav analize. Silvouple repran li: tou lapes vizib, "
                                   "bon lalimier, san refle.")
            resp.provider = ProviderInfo(mode="mock", provider_name="quality-gate", model="none",
                                         real_inference=False, latency_ms=0)
            resp.limitations = _limitations(["No model call was made for this invalid image (token saving)."])
            _persist_analysis(session, analysis, resp)
            response.headers["X-Inference-Provider"] = _provider_tag(resp.provider)
            return resp
        dup = session.exec(
            select(CatchAnalysis).where(CatchAnalysis.image_sha256 == image_sha,
                                        CatchAnalysis.analysis_id != analysis.analysis_id)
        ).first()
        if dup:
            resp.image_quality.warnings.append("duplicate_of_previous_upload")

    candidates = [public_candidate(s) for s in candidates_for(note)]
    ctx = ToolContext(session=session, language=language, allow_network=True, analysis_id=analysis.analysis_id)
    result = provider_analyse(provider_mode, image_jpeg, image_sha, note, language, candidates, ctx)

    resp.intent = result.intent  # type: ignore[assignment]
    resp.visible_characteristics = result.visible_characteristics
    resp.confidence_label = result.confidence_label  # type: ignore[assignment]
    resp.estimated_size_unverified_cm = result.estimated_size_unverified_cm
    resp.reply = result.reply
    resp.reply_morisyen = result.reply_morisyen
    resp.recommended_next_step = result.recommended_next_step  # type: ignore[assignment]
    resp.function_trace = result.function_trace
    resp.provider = ProviderInfo(mode=result.mode, provider_name=result.provider_name,  # type: ignore[arg-type]
                                 model=result.model, real_inference=result.real_inference,
                                 latency_ms=result.latency_ms)
    if result.species_id:
        sp = get_species(result.species_id)
        if sp:
            resp.species_suggestion = SpeciesSuggestion(
                species_id=sp["species_id"], morisyen=sp["morisyen"],
                english=sp["english"], scientific=sp["scientific"])
    resp.legal_check = LegalCheck(status="pending_confirmation", rule=None, source_id=None,
                                  note="Rule checking runs only after species confirmation with a measured length.")
    resp.limitations = _limitations(result.disclosures)

    analysis.image_sha256 = image_sha
    _persist_analysis(session, analysis, resp)
    response.headers["X-Inference-Provider"] = _provider_tag(resp.provider)
    return resp


def _provider_tag(provider: ProviderInfo) -> str:
    """Per-request provider record, `mode:model` — the header half of the
    honesty trail (the persistent half lives on CatchAnalysis and, after
    confirmation, CatchRecord.analysis_provider)."""
    return f"{provider.mode}:{provider.model or provider.provider_name or 'none'}"


def _persist_analysis(session: Session, analysis: CatchAnalysis, resp: AnalyseCatchResponse) -> None:
    analysis.intent = resp.intent
    analysis.image_quality_status = resp.image_quality.status
    analysis.blur_score = resp.image_quality.blur_score
    analysis.brightness = resp.image_quality.brightness
    analysis.suggested_species_id = resp.species_suggestion.species_id
    analysis.confidence_label = resp.confidence_label
    analysis.estimated_size_unverified_cm = resp.estimated_size_unverified_cm
    analysis.provider_mode = resp.provider.mode
    analysis.provider_model = resp.provider.model
    analysis.real_inference = resp.provider.real_inference
    analysis.latency_ms = resp.provider.latency_ms
    session.add(analysis)
    session.commit()


@router.post(
    "/api/analyses/{analysis_id}/confirm",
    response_model=ConfirmResponse,
    summary="Confirm a species + measured length, and run the legal-status rule check",
    responses={200: {"content": {"application/json": {"example": {
        "catch_record_id": "b6b0e6a1-7c9e-4b3a-9b1a-3b6a2f9e0a11",
        "species_id": "octopus_cyanea",
        "legal_check": {"status": "allowed", "rule": "R-OCT-CLOSE-2016", "source_id": "S1",
                        "verification_status": "provisional",
                        "note": "No closure or size rule triggered on 2026-07-29. Verify against the latest official fisheries notice."},
        "measured_length_cm": 42.0, "count": 1, "capture_date": "2026-07-29",
        "limitations": ["Lamer Konekte provides AI-assisted catch documentation and informational guidance. "
                       "Species suggestions and regulatory checks must be confirmed against official sources "
                       "and by the fisher or an authorised officer.",
                       "Verify against the latest official fisheries notice."],
    }}}}},
)
def confirm_analysis(analysis_id: str, body: ConfirmRequest,
                     session: Session = Depends(get_session)) -> ConfirmResponse:
    """The ONLY place deterministic rule checking runs — after human confirmation,
    using measured_length_cm exclusively (never the AI estimate)."""
    analysis = session.get(CatchAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(404, "analysis not found")
    if not get_species(body.confirmed_species_id):
        raise HTTPException(422, "unknown species_id")

    current, simulated = demo_date.get_current_date(session)
    capture = date.fromisoformat(body.capture_date) if body.capture_date else current
    check = check_confirmed_catch(body.confirmed_species_id, body.measured_length_cm, capture)

    record = CatchRecord(
        analysis_id=analysis_id,
        species_id=body.confirmed_species_id,
        measured_length_cm=body.measured_length_cm,
        count=body.count,
        capture_date=capture.isoformat(),
        fishing_area=body.fishing_area,
        latitude_rounded=round(body.latitude, 2) if body.latitude is not None else None,
        longitude_rounded=round(body.longitude, 2) if body.longitude is not None else None,
        legal_status=check.status if check.status != "pending_confirmation" else "unknown",
        legal_rule_id=check.rule,
        legal_note=check.note or "",
        analysis_provider=(f"{analysis.provider_mode}:{analysis.provider_model or 'none'}"
                           if analysis.provider_mode else None),
    )
    analysis.confirmed = True
    session.add(record)
    session.add(analysis)
    session.commit()
    session.refresh(record)
    ledger.append_record(session, record)

    extra = [RULE_VERIFY_NOTICE]
    if simulated:
        extra.append(f"Simulated demo date in use: {capture.isoformat()}.")
    return ConfirmResponse(
        catch_record_id=record.id, species_id=record.species_id, legal_check=check,
        measured_length_cm=record.measured_length_cm, count=record.count,
        capture_date=record.capture_date, limitations=_limitations(extra),
    )


@router.get(
    "/api/species",
    summary="List the species catalogue (Morisyen + English + scientific names)",
    responses={200: {"content": {"application/json": {"example": {"species": [
        {"species_id": "octopus_cyanea", "scientific": "Octopus cyanea", "english": "Day octopus",
         "morisyen": "ourite", "morisyen_status": "provisional",
         "visible_characteristics": ["eight arms with suckers", "no fins or scales",
                                     "colour-changing mottled skin", "bulbous mantle"]},
    ]}}}}},
)
def list_species() -> dict:
    return {"species": [public_candidate(s) for s in load_catalogue()]}


@router.get("/api/species/{species_id}")
def species_detail(species_id: str) -> dict:
    sp = get_species(species_id)
    if not sp:
        raise HTTPException(404, "species not found")
    return public_candidate(sp)


@router.get(
    "/api/rules/static",
    summary="The complete rules dataset, verbatim (Workstream 2: offline assistant)",
    description=("Returns the three JSON files that are the app's regulatory source of truth "
                 "(species rules, species catalogue, source register), unmodified. The offline "
                 "assistant bundles the same files at build time and uses this endpoint only to "
                 "detect that its bundle is stale — rules_version is the comparison key."),
)
def rules_static() -> dict:
    s = get_settings()
    payload: dict = {}
    for key, rel in (("rules", "rules/species_rules.json"),
                     ("catalogue", "processed/species_catalogue.json"),
                     ("sources", "rules/source_register.json")):
        with open(s.data_dir / rel, encoding="utf-8") as f:
            payload[key] = json.load(f)
    payload["rules_version"] = payload["rules"].get("rules_version")
    return payload


@router.get(
    "/api/catches",
    summary="List saved catch records, most recent first",
)
def list_catches(limit: int = 50, session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(CatchRecord).order_by(CatchRecord.created_at.desc()).limit(min(limit, 200))).all()  # type: ignore[union-attr]
    return {"catches": [r.model_dump() for r in rows]}


@router.post(
    "/api/catches",
    response_model=ConfirmResponse,
    summary="Log a catch directly, bypassing photo analysis (manual / offline-sync entry)",
)
def create_catch(body: ConfirmRequest, session: Session = Depends(get_session)) -> ConfirmResponse:
    """Manual catch logging (offline flow) — same deterministic rule path as confirm."""
    if not get_species(body.confirmed_species_id):
        raise HTTPException(422, "unknown species_id")
    current, simulated = demo_date.get_current_date(session)
    capture = date.fromisoformat(body.capture_date) if body.capture_date else current
    check = check_confirmed_catch(body.confirmed_species_id, body.measured_length_cm, capture)
    record = CatchRecord(
        species_id=body.confirmed_species_id, measured_length_cm=body.measured_length_cm,
        count=body.count, capture_date=capture.isoformat(), fishing_area=body.fishing_area,
        latitude_rounded=round(body.latitude, 2) if body.latitude is not None else None,
        longitude_rounded=round(body.longitude, 2) if body.longitude is not None else None,
        legal_status=check.status if check.status != "pending_confirmation" else "unknown",
        legal_rule_id=check.rule, legal_note=check.note or "",
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    ledger.append_record(session, record)
    extra = [RULE_VERIFY_NOTICE] + ([f"Simulated demo date in use: {capture.isoformat()}."] if simulated else [])
    return ConfirmResponse(catch_record_id=record.id, species_id=record.species_id, legal_check=check,
                           measured_length_cm=record.measured_length_cm, count=record.count,
                           capture_date=record.capture_date, limitations=_limitations(extra))


@router.get("/api/catches/{catch_id}")
def catch_detail(catch_id: str, session: Session = Depends(get_session)) -> dict:
    row = session.get(CatchRecord, catch_id)
    if not row:
        raise HTTPException(404, "catch not found")
    return row.model_dump()


# --- Traceability: ledger, certificates, submissions -------------------------
# Backs the authority dashboard (/authority) and the public verification page
# (/verify/:id). Every response states the limits of what the chain proves.

LEDGER_SCOPE_NOTE = (
    "This chain proves a record has not been altered or removed since it was logged. "
    "It does NOT verify that the original catch details were reported truthfully. "
    "The ledger is local to this deployment, not a distributed blockchain."
)


@router.get(
    "/api/ledger",
    summary="Inspect the catch-record hash chain (officer view)",
    description="Entries in sequence, each committing to its record's content and to the previous entry.",
)
def ledger_chain(limit: int = 200, session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(LedgerEntry).order_by(LedgerEntry.seq).limit(min(limit, 1000))).all()  # type: ignore[union-attr,arg-type]
    return {
        "entries": [
            {"seq": e.seq, "record_id": e.record_id, "payload_sha256": e.payload_sha256,
             "prev_hash": e.prev_hash, "entry_hash": e.entry_hash,
             "created_at": e.created_at.isoformat()}
            for e in rows
        ],
        "genesis_hash": ledger.GENESIS_HASH,
        "count": len(rows),
        "scope_note": LEDGER_SCOPE_NOTE,
    }


@router.get(
    "/api/ledger/verify",
    summary="Walk the chain and report intact or broken, naming the first bad record",
    responses={200: {"content": {"application/json": {"example": {
        "status": "intact", "entries": 12, "verified_through": 12, "broken_at": None,
        "detail": "All 12 entries verified from genesis. No record has been altered since it was logged.",
        "scope_note": LEDGER_SCOPE_NOTE,
    }}}}},
)
def ledger_verify(session: Session = Depends(get_session)) -> dict:
    result = ledger.verify_chain(session)
    result["scope_note"] = LEDGER_SCOPE_NOTE
    return result


@router.get(
    "/api/verify/{record_id}",
    summary="Public certificate verification (no auth) — verified | not_found | chain_broken",
    description="Backs the QR-code landing page. Deliberately states what it does not prove.",
)
def verify_certificate(record_id: str, session: Session = Depends(get_session)) -> dict:
    record = session.get(CatchRecord, record_id)
    entry = ledger.entry_for_record(session, record_id)

    if record is None or entry is None:
        return {
            "verdict": "not_found",
            "record_id": record_id,
            "headline": "No certificate found for this reference.",
            "detail": ("This reference does not match any sealed catch record in this deployment. "
                       "Check the reference, or the certificate may not originate from this system."),
            "scope_note": LEDGER_SCOPE_NOTE,
            "limitations": _limitations(),
        }

    chain = ledger.verify_chain(session)
    tampered = ledger.payload_hash(record) != entry.payload_sha256
    # A break anywhere at or before this entry invalidates this record's proof.
    broken_at_or_before = (
        chain["status"] == "broken"
        and chain["broken_at"] is not None
        and entry.seq is not None
        and chain["broken_at"]["seq"] <= entry.seq
    )

    if tampered or broken_at_or_before:
        return {
            "verdict": "chain_broken",
            "record_id": record_id,
            "headline": "This record has changed since it was logged.",
            "detail": (chain["detail"] if broken_at_or_before else
                       "The record's contents no longer match the value sealed onto the ledger."),
            "broken_at": chain["broken_at"],
            "scope_note": LEDGER_SCOPE_NOTE,
            "limitations": _limitations(),
        }

    species = get_species(record.species_id) or {}
    return {
        "verdict": "verified",
        "record_id": record_id,
        "headline": "This record is unaltered since it was logged.",
        "detail": ("The sealed value still matches the record, and every link before it verifies. "
                   "This confirms the record was not edited after logging."),
        "verified": {
            "species_id": record.species_id,
            "species_english": species.get("english"),
            "species_morisyen": species.get("morisyen"),
            "species_morisyen_status": species.get("morisyen_status"),
            "measured_length_cm": record.measured_length_cm,
            "count": record.count,
            "capture_date": record.capture_date,
            "fishing_area": record.fishing_area,
            "sealed_at": entry.created_at.isoformat(),
            "ledger_seq": entry.seq,
            "entry_hash": entry.entry_hash,
            "prev_hash": entry.prev_hash,
        },
        "not_verified": [
            "That the species identification is correct — it was AI-assisted and confirmed by the fisher, not independently verified.",
            "That the measurement is accurate — it is self-reported by the fisher.",
            "That the catch was legally taken — see the fisheries rule status, which is informational only.",
        ],
        "legal_status_informational": {
            "status": record.legal_status,
            "rule_id": record.legal_rule_id,
            "note": RULE_VERIFY_NOTICE,
        },
        "scope_note": LEDGER_SCOPE_NOTE,
        "limitations": _limitations(),
    }


@router.get(
    "/api/submissions",
    summary="List declaration submissions (officer view)",
)
def list_submissions(session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(Declaration).order_by(Declaration.created_at.desc())).all()  # type: ignore[union-attr]
    out = []
    for d in rows:
        catches = json.loads(d.catches_json)
        out.append({
            "declaration_id": d.id,
            "fisher_name": d.fisher_name,
            "fishing_area": d.fishing_area,
            "period_start": d.period_start,
            "period_end": d.period_end,
            "record_count": len(catches),
            "total_count": sum(int(c.get("count") or 0) for c in catches),
            "status": d.status,
            "mock_receipt_id": d.mock_receipt_id,
            "submitted_at": d.created_at.isoformat(),
        })
    return {"submissions": out, "count": len(out), "mock_label": declarations.MOCK_LABEL}


@router.get(
    "/api/submissions/{declaration_id}",
    summary="Submission detail with per-record ledger status (officer view)",
)
def submission_detail(declaration_id: str, session: Session = Depends(get_session)) -> dict:
    decl = session.get(Declaration, declaration_id)
    if not decl:
        raise HTTPException(404, "submission not found")

    records = []
    for c in json.loads(decl.catches_json):
        rid = c.get("record_id") or c.get("id")
        entry = ledger.entry_for_record(session, rid) if rid else None
        records.append({
            **c,
            "record_id": rid,
            "ledger_seq": entry.seq if entry else None,
            "entry_hash": entry.entry_hash if entry else None,
            "sealed": entry is not None,
        })

    return {
        "declaration_id": decl.id,
        "fisher_name": decl.fisher_name,
        "fishing_area": decl.fishing_area,
        "period_start": decl.period_start,
        "period_end": decl.period_end,
        "status": decl.status,
        "mock_receipt_id": decl.mock_receipt_id,
        "submitted_at": decl.created_at.isoformat(),
        "records": records,
        "chain": ledger.verify_chain(session),
        "mock_label": declarations.MOCK_LABEL,
        "officer_action_note": ("Verification actions are advisory-assisted and recorded as the officer's "
                                "decision. Nothing here is automated or legally binding."),
        "scope_note": LEDGER_SCOPE_NOTE,
    }


@router.get("/api/reports/today")
def report_today(session: Session = Depends(get_session)) -> dict:
    d, simulated = demo_date.get_current_date(session)
    rows = session.exec(select(CatchRecord).where(CatchRecord.capture_date == d.isoformat())).all()
    by_species: dict[str, int] = {}
    for r in rows:
        by_species[r.species_id] = by_species.get(r.species_id, 0) + r.count
    return {"date": d.isoformat(), "date_simulated": simulated, "total_records": len(rows),
            "total_count": sum(r.count for r in rows), "by_species": by_species}


@router.post(
    "/api/declarations/prepare",
    summary="Draft a declaration from saved catches in a date range (period_start/period_end are YYYY-MM-DD)",
)
def prepare_declaration(fisher_name: str = Form(default=""), fishing_area: str = Form(default=""),
                        period_start: str = Form(..., description="YYYY-MM-DD, inclusive"),
                        period_end: str = Form(..., description="YYYY-MM-DD, inclusive"),
                        session: Session = Depends(get_session)) -> dict:
    decl = declarations.prepare(session, fisher_name, fishing_area, period_start, period_end)
    return {"declaration_id": decl.id, "status": decl.status,
            "catches": json.loads(decl.catches_json), "mock_label": declarations.MOCK_LABEL}


@router.post(
    "/api/declarations/mock-submit",
    summary="Mock-submit a declaration (demonstration only — never contacts a real government system)",
)
def mock_submit_declaration(declaration_id: str = Form(...), session: Session = Depends(get_session)) -> dict:
    decl = declarations.mock_submit(session, declaration_id)
    if not decl:
        raise HTTPException(404, "declaration not found")
    return {"declaration_id": decl.id, "status": decl.status, "mock_receipt_id": decl.mock_receipt_id,
            "mock_label": declarations.MOCK_LABEL,
            "notice": "This is a demonstration receipt. No official government system was contacted."}


@router.get("/api/declarations/{declaration_id}/pdf")
def declaration_pdf(declaration_id: str, session: Session = Depends(get_session)) -> FileResponse:
    decl = session.get(Declaration, declaration_id)
    if not decl:
        raise HTTPException(404, "declaration not found")
    path = declarations.export_pdf(decl)
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.get(
    "/api/marine-conditions",
    summary="Current sea/wave conditions near a point (Open-Meteo; informational only)",
    description=("Grand Baie, Mahebourg and Flic-en-Flac are pre-warmed into cache at server startup, "
                "so requests near those towns return instantly instead of waiting on Open-Meteo."),
    responses={200: {"content": {"application/json": {"example": {
        "location": "-20.01,57.58", "source": "open-meteo",
        "attribution": "Weather data by Open-Meteo.com (CC-BY 4.0)",
        "disclaimer": ("Marine forecasts are informational and may be incomplete near the coast. "
                      "Confirm conditions through official local marine advisories before travelling."),
        "mock": False, "time": "2026-07-29T12:00", "wave_height_m": 0.9, "wave_direction_deg": 140,
        "wave_period_s": 7.5, "swell_height_m": 1.3, "swell_direction_deg": 195, "swell_period_s": 11.4,
        "sea_surface_temperature_c": 24.6, "stale": False, "cached": True,
    }}}}},
)
def marine_conditions(latitude: float | None = None, longitude: float | None = None,
                      session: Session = Depends(get_session)) -> dict:
    data = get_marine_conditions(session, latitude, longitude)
    data["disclaimer"] = MARINE_DISCLAIMER
    return data


@router.post("/api/audio/analyse")
def audio_analyse() -> dict:
    """Honest audio gate response: no audio-capable Gemma model has passed the gate."""
    return {
        "status": "unavailable",
        "reason": ("The audio workstream has not passed its quality gate (no local audio-capable "
                   "Gemma run has been completed). Typed Morisyen or English remains the input path."),
        "limitations": _limitations(),
    }


@router.get("/api/sync/queue")
def sync_queue(session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(SyncQueueItem).order_by(SyncQueueItem.created_at)).all()  # type: ignore[union-attr]
    return {"items": [r.model_dump() for r in rows],
            "queued": sum(1 for r in rows if r.status == "queued")}


@router.post("/api/sync/queue")
def sync_enqueue(kind: str = Form(default="catch_record"), payload: str = Form(default="{}"),
                 session: Session = Depends(get_session)) -> dict:
    try:
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(422, "payload must be a JSON object") from None
    item = SyncQueueItem(kind=kind[:40], payload_json=json.dumps(parsed)[:4000])
    session.add(item)
    session.commit()
    session.refresh(item)
    return {"queue_item_id": item.id, "status": item.status}


@router.post("/api/sync/process")
def sync_process(session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(SyncQueueItem).where(SyncQueueItem.status == "queued")).all()
    processed, failed = 0, 0
    for item in rows:
        try:
            payload = json.loads(item.payload_json)
            if item.kind == "catch_record" and payload.get("species_id"):
                body = ConfirmRequest(confirmed_species_id=payload["species_id"],
                                      measured_length_cm=payload.get("measured_length_cm"),
                                      count=int(payload.get("count", 1)),
                                      capture_date=payload.get("capture_date"),
                                      fishing_area=payload.get("fishing_area", ""))
                create_catch(body, session)
            item.status = "processed"
            processed += 1
        except Exception:  # noqa: BLE001
            item.status = "failed"
            failed += 1
        session.add(item)
    session.commit()
    return {"processed": processed, "failed": failed}


@router.post("/api/demo/set-date")
def demo_set_date(simulated_date: str = Form(...), session: Session = Depends(get_session)) -> dict:
    try:
        demo_date.set_simulated_date(session, simulated_date)
    except ValueError:
        raise HTTPException(422, "simulated_date must be YYYY-MM-DD") from None
    return {"simulated_date": simulated_date, "date_simulated": True,
            "notice": "The UI must display a prominent simulated-date badge."}


@router.post("/api/demo/reset")
def demo_reset(session: Session = Depends(get_session)) -> dict:
    demo_date.set_simulated_date(session, None)
    # LedgerEntry must be cleared alongside CatchRecord: a chain left pointing at
    # deleted records would report "broken" forever after a demo reset.
    # AisPosition is swept too (Task 4b, deliberate): /api/demo/reset exists to
    # make the demo repeatable, and a transport brief still showing vessels from
    # a previous run would have no other way to be cleared. Nothing is lost —
    # with the collector running the rolling window refills from the live feed
    # within seconds, and otherwise it re-seeds on the next request.
    for model in (CatchRecord, CatchAnalysis, Declaration, LedgerEntry, SyncQueueItem,
                  ToolTrace, AisPosition):
        for row in session.exec(select(model)).all():
            session.delete(row)
    session.commit()
    _analyse_limiter.reset()
    _reset_pillar_limiters()
    return {"status": "reset", "date_simulated": False}


@router.get("/api/demo/fixtures")
def demo_fixtures() -> dict:
    path = get_settings().data_dir / "demo" / "fixtures.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"cases": []}


# --------------------------------------------------------------- manual AI test console

_console_limiter = InMemoryRateLimiter(limit=6, window_seconds=60.0)

# Server-side classification of a failure that never reached a model assertion. A hosted
# 5xx, a DNS drop or a timeout says nothing about the model's behaviour, so the console
# must not present it as an AI result — and the frontend must not discard a good trace
# because the Wi-Fi blinked. Behavioural failures are the opposite: they ARE the result.
_TRANSIENT_ERROR = re.compile(
    r"\b(429|500|502|503|504)\b|RESOURCE_EXHAUSTED|UNAVAILABLE|DEADLINE_EXCEEDED"
    r"|ConnectError|ConnectTimeout|ReadTimeout|RemoteProtocolError|getaddrinfo"
    r"|Connection reset|Server disconnected|Timeout", re.I)

# Phrases the product must never ASSERT about going to sea. Same intent as the live gate
# runner's check, reported here as a visible flag.
_GUARANTEE = re.compile(r"(100\s*%?\s*safe|guaranteed safe|it is safe to (go|sail|travel)"
                        r"|definitely safe|safe to go out|no risk)", re.I)

# A refusal necessarily quotes the phrase it is refusing: "I cannot say if it is 100% safe"
# is the behaviour we want, but a naive match flags it as a guarantee — which would tell the
# tester the app made a promise when it explicitly declined to. So a match only counts when
# it is not negated by the words just before it.
_NEGATED = re.compile(r"(cannot|can't|can not|won't|will not|unable|never|not\b|no one|nobody"
                      r"|pa kapav|napa|pa\b|zame)[^.!?]{0,60}$", re.I)


def _asserts_safety_guarantee(text: str) -> bool:
    """True only when a safety guarantee is stated, not quoted in order to refuse it."""
    for m in _GUARANTEE.finditer(text):
        if not _NEGATED.search(text[:m.start()]):
            return True
    return False


@router.post(
    "/api/ai/test-console",
    response_model=ConsoleResponse,
    summary="Manual AI test console — run one free-text prompt through the production pipeline",
    description=(
        "Developer/demo surface for the Technical Proof page. Runs the **same** production "
        "inference path as `/api/analyse-catch` (same system instruction, same structured-output "
        "validation, same allow-listed tool registry with Pydantic argument validation), and "
        "returns only safe, displayable metadata.\n\n"
        "The provider is always the configured production default — it cannot be chosen by the "
        "caller, and the rejected fine-tuned E2B adapter is not reachable. No secret, prompt "
        "text, chain of thought or argument *value* is ever returned. Rate-limited to 6/min. "
        "Unlike `/api/analyse-catch` this writes no catch analysis, so console experiments never "
        "appear in the fisher's catch log."
    ),
    responses={429: {"description": "Rate limit exceeded (6 requests/minute per client address)."}},
)
def ai_test_console(
    request: Request,
    body: ConsoleRequest,
    session: Session = Depends(get_session),
) -> ConsoleResponse:
    if not _console_limiter.allow(_client_ip(request)):
        raise HTTPException(429, "Too many console requests from this address — please wait a minute.",
                            headers={"Retry-After": "60"})

    prompt = body.prompt.strip()
    candidates = [public_candidate(s) for s in candidates_for(prompt)]
    # analysis_id stays None: the console must not manufacture a CatchAnalysis row.
    ctx = ToolContext(session=session, language=body.language, allow_network=True, analysis_id=None)

    try:
        # The production dispatcher, with no provider override — exactly what the app uses.
        result = provider_analyse(None, None, None, prompt, body.language, candidates, ctx)
    except Exception as e:  # noqa: BLE001 — surfaced as a controlled error, never a 500
        log.warning("test console request failed: %s", type(e).__name__)
        kind = "transient" if _TRANSIENT_ERROR.search(f"{type(e).__name__}: {e}") else "behavioural"
        return ConsoleResponse(controlled_error=ConsoleError(
            kind=kind,
            message=("The hosted model could not be reached. This is a transport or capacity "
                     "problem, not a model result — retry in a moment."
                     if kind == "transient" else
                     f"The request failed in a controlled way ({type(e).__name__}).")))

    executed = [t.function for t in result.function_trace if t.final_action == "executed"]
    marine_ran = "get_marine_conditions" in executed
    text = f"{result.reply}\n{result.reply_morisyen}"

    disclosures = _limitations(result.disclosures)
    if marine_ran:
        # Server-injected, exactly as elsewhere: the model cannot remove it.
        disclosures.append(MARINE_DISCLAIMER)
    mock_used = not result.real_inference

    # The dispatcher absorbs a hosted failure and returns the disclosed mock — correct
    # product behaviour, but the console must still say WHY, so the tester knows this was
    # a capacity/transport blip to retry rather than the model behaving this way. The
    # result is returned in full alongside the note; nothing is hidden or discarded.
    fell_back = FALLBACK_DISCLOSURE in result.disclosures
    transient_note = ConsoleError(
        kind="transient",
        message=("The hosted model was unavailable, so this answer came from the disclosed "
                 "deterministic mock — a transport or capacity problem, not a model result. "
                 "Retry in a moment for real inference."),
    ) if fell_back else None

    return ConsoleResponse(
        final_response=result.reply,
        reply_morisyen=result.reply_morisyen,
        intent=result.intent,
        provider=result.provider_name,
        model=result.model or "none",
        real_inference=result.real_inference,
        latency_ms=result.latency_ms,
        # "Selected" is the last allow-listed function actually executed; functions_called
        # keeps the whole ordered chain, so a date-then-conditions resolution is visible.
        selected_function=executed[-1] if executed else None,
        functions_called=executed,
        argument_names=sorted({n for t in result.function_trace for n in t.argument_names}),
        tool_round_trip_completed=bool(executed) and bool(result.reply.strip()),
        schema_valid=bool(result.diagnostics.get("final_schema_valid", False)),
        safety_flags={
            "marine_disclaimer_present": (MARINE_DISCLAIMER in disclosures) if marine_ran else True,
            "no_safety_guarantee": not _asserts_safety_guarantee(text),
            "permanent_limitation_present": PERMANENT_LIMITATION in disclosures,
            "no_unknown_function_executed": all(
                t.result_status != "unknown_function" or t.final_action == "rejected"
                for t in result.function_trace),
        },
        mock_used=mock_used,
        mock_label="MOCK — not real model inference" if mock_used else "",
        disclosures=disclosures,
        function_trace=result.function_trace,
        controlled_error=transient_note,
    )
