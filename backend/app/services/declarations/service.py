"""Declaration drafts, PDF export and the clearly-labelled MOCK ministry submission.

The mock endpoint is a demonstration only. Every artefact it produces carries the
MOCK label; nothing here contacts any real government system.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.entities import CatchRecord, Declaration

MOCK_LABEL = "MOCK DEMONSTRATION — NOT AN OFFICIAL GOVERNMENT SUBMISSION"


def prepare(session: Session, fisher_name: str, fishing_area: str, period_start: str, period_end: str) -> Declaration:
    records = session.exec(
        select(CatchRecord).where(CatchRecord.capture_date >= period_start, CatchRecord.capture_date <= period_end)
    ).all()
    catches = [
        {
            # record_id lets the officer view resolve each line to its ledger entry.
            "record_id": r.id,
            "species_id": r.species_id,
            "measured_length_cm": r.measured_length_cm,
            "count": r.count,
            "capture_date": r.capture_date,
            "legal_status": r.legal_status,
        }
        for r in records
    ]
    decl = Declaration(
        fisher_name=fisher_name, fishing_area=fishing_area,
        period_start=period_start, period_end=period_end,
        catches_json=json.dumps(catches), status="draft",
    )
    session.add(decl)
    session.commit()
    session.refresh(decl)
    return decl


def mock_submit(session: Session, declaration_id: str) -> Declaration | None:
    decl = session.get(Declaration, declaration_id)
    if not decl:
        return None
    decl.status = "mock_submitted"
    decl.mock_receipt_id = f"MOCK-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
    session.add(decl)
    session.commit()
    session.refresh(decl)
    return decl


# fpdf's built-in core fonts are Latin-1 only, so a single em-dash in MOCK_LABEL made
# every PDF export raise FPDFUnicodeEncodingException (a real 500 on
# GET /api/declarations/{id}/pdf). Transliterate the handful of typographic characters
# our strings use instead of swapping in a Unicode font — the MOCK wording is
# safety-critical and must survive verbatim apart from the dash.
_PDF_TRANSLITERATE = {
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", " ": " ",
}


def _pdf_safe(text: str) -> str:
    """Latin-1-safe text for fpdf core fonts, preserving meaning."""
    for bad, good in _PDF_TRANSLITERATE.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def export_pdf(decl: Declaration) -> Path:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, _pdf_safe("Lamer Konekte - Catch Declaration Draft"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(200, 30, 30)
    pdf.cell(0, 8, _pdf_safe(MOCK_LABEL), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, _pdf_safe(f"Fisher: {decl.fisher_name}   Area: {decl.fishing_area}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, _pdf_safe(f"Period: {decl.period_start} to {decl.period_end}   Status: {decl.status}"), new_x="LMARGIN", new_y="NEXT")
    if decl.mock_receipt_id:
        pdf.cell(0, 8, _pdf_safe(f"Mock receipt: {decl.mock_receipt_id}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for c in json.loads(decl.catches_json):
        line = (f"- {c['capture_date']}  {c['species_id']}  x{c['count']}  "
                f"{c['measured_length_cm'] or '?'} cm  legal: {c['legal_status']}")
        pdf.cell(0, 7, _pdf_safe(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5, _pdf_safe("Species suggestions and regulatory checks must be confirmed against official "
                          "sources and by the fisher or an authorised officer."))
    out = get_settings().storage_dir / f"declaration_{decl.id}.pdf"
    pdf.output(str(out))
    return out
