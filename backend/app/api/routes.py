from __future__ import annotations

import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.limitations import (MARINE_DISCLAIMER, MOCK_DISCLOSURE,
                                  PERMANENT_LIMITATION, RULE_VERIFY_NOTICE)
from app.db.session import get_session
from app.models.entities import (CatchAnalysis, CatchRecord, Declaration,
                                 SyncQueueItem, ToolTrace)
from app.providers.dispatcher import analyse as provider_analyse
from app.schemas.analysis import (AnalyseCatchResponse, ConfirmRequest,
                                  ConfirmResponse, LegalCheck, ProviderInfo,
                                  SpeciesSuggestion)
from app.services.declarations import service as declarations
from app.services.fisheries_rules import demo_date
from app.services.fisheries_rules.engine import check_confirmed_catch
from app.services.marine.client import get_marine_conditions
from app.services.species.retrieval import (candidates_for, get_species,
                                            load_catalogue, public_candidate)
from app.services.vision.quality import assess
from app.tools.registry import ToolContext

log = logging.getLogger(__name__)
router = APIRouter()


def _limitations(extra: list[str] | None = None) -> list[str]:
    out = [PERMANENT_LIMITATION]
    if extra:
        out.extend(extra)
    return out


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
    }


@router.post("/api/analyse-catch", response_model=AnalyseCatchResponse)
async def analyse_catch(
    image: UploadFile | None = File(default=None),
    note: str | None = Form(default=None),
    language: str = Form(default="en"),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    fishing_area: str = Form(default=""),
    provider_mode: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> AnalyseCatchResponse:
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
    return resp


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


@router.post("/api/analyses/{analysis_id}/confirm", response_model=ConfirmResponse)
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
    )
    analysis.confirmed = True
    session.add(record)
    session.add(analysis)
    session.commit()
    session.refresh(record)

    extra = [RULE_VERIFY_NOTICE]
    if simulated:
        extra.append(f"Simulated demo date in use: {capture.isoformat()}.")
    return ConfirmResponse(
        catch_record_id=record.id, species_id=record.species_id, legal_check=check,
        measured_length_cm=record.measured_length_cm, count=record.count,
        capture_date=record.capture_date, limitations=_limitations(extra),
    )


@router.get("/api/species")
def list_species() -> dict:
    return {"species": [public_candidate(s) for s in load_catalogue()]}


@router.get("/api/species/{species_id}")
def species_detail(species_id: str) -> dict:
    sp = get_species(species_id)
    if not sp:
        raise HTTPException(404, "species not found")
    return public_candidate(sp)


@router.get("/api/catches")
def list_catches(limit: int = 50, session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(CatchRecord).order_by(CatchRecord.created_at.desc()).limit(min(limit, 200))).all()  # type: ignore[union-attr]
    return {"catches": [r.model_dump() for r in rows]}


@router.post("/api/catches", response_model=ConfirmResponse)
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


@router.get("/api/reports/today")
def report_today(session: Session = Depends(get_session)) -> dict:
    d, simulated = demo_date.get_current_date(session)
    rows = session.exec(select(CatchRecord).where(CatchRecord.capture_date == d.isoformat())).all()
    by_species: dict[str, int] = {}
    for r in rows:
        by_species[r.species_id] = by_species.get(r.species_id, 0) + r.count
    return {"date": d.isoformat(), "date_simulated": simulated, "total_records": len(rows),
            "total_count": sum(r.count for r in rows), "by_species": by_species}


@router.post("/api/declarations/prepare")
def prepare_declaration(fisher_name: str = Form(default=""), fishing_area: str = Form(default=""),
                        period_start: str = Form(...), period_end: str = Form(...),
                        session: Session = Depends(get_session)) -> dict:
    decl = declarations.prepare(session, fisher_name, fishing_area, period_start, period_end)
    return {"declaration_id": decl.id, "status": decl.status,
            "catches": json.loads(decl.catches_json), "mock_label": declarations.MOCK_LABEL}


@router.post("/api/declarations/mock-submit")
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


@router.get("/api/marine-conditions")
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
    for model in (CatchRecord, CatchAnalysis, Declaration, SyncQueueItem, ToolTrace):
        for row in session.exec(select(model)).all():
            session.delete(row)
    session.commit()
    return {"status": "reset", "date_simulated": False}


@router.get("/api/demo/fixtures")
def demo_fixtures() -> dict:
    path = get_settings().data_dir / "demo" / "fixtures.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"cases": []}
