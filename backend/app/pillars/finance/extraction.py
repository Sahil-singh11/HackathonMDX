"""PDF text extraction and span-provenance verification.

The model NEVER gets to assert a field is supported. It proposes a value plus
a claimed page and quote; this module — plain code — checks whether that
quote genuinely appears on that page of the actual extracted text. Only then
is the field marked supported. Anything else (no page/quote given, the quote
doesn't appear, the page is out of range) is unsupported — a finding in
itself, per Task 6b's own instruction, not a silent blank.
"""
from __future__ import annotations

import json
import re
from io import BytesIO

from pypdf import PdfReader

from app.pillars.finance.schemas import ExtractedField

EXPECTED_FIELDS = (
    "use_of_proceeds_category", "evaluation_process_summary",
    "management_of_proceeds_summary", "impact_metrics",
    "reporting_commitment", "verification_commitment",
)


def extract_pdf_pages(pdf_bytes: bytes) -> list[str]:
    """One string per page, 1-indexed conceptually (callers use page - 1)."""
    reader = PdfReader(BytesIO(pdf_bytes))
    return [(page.extract_text() or "") for page in reader.pages]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def locate_span(pages: list[str], claimed_page: int | None, claimed_span: str | None) -> tuple[bool, str]:
    """Verify a claimed (page, span) against the real extracted text.

    Returns (supported, reason_if_not). Whitespace-normalised substring match
    — deliberately simple and inspectable, not fuzzy scoring that could paper
    over a claim the source text does not actually contain.
    """
    if not claimed_span or not claimed_span.strip():
        return False, "model gave no supporting span"
    if claimed_page is None:
        return False, "model gave no page number"
    if not (1 <= claimed_page <= len(pages)):
        return False, f"claimed page {claimed_page} is out of range (document has {len(pages)} pages)"

    haystack = _normalise(pages[claimed_page - 1])
    needle = _normalise(claimed_span)
    if not needle or needle not in haystack:
        return False, f"claimed span not found in the extracted text of page {claimed_page}"
    return True, ""


def fields_from_model_json(raw_text: str, pages: list[str]) -> list[ExtractedField]:
    """Parse the model's proposed extraction and verify every span.

    Never trusts the model's own notion of support: `supported` is always
    computed here via locate_span, regardless of what the model claimed.
    A response that fails to parse as JSON, or omits a field entirely,
    produces an unsupported ExtractedField for that field — never a crash,
    never a silently-met criterion.
    """
    try:
        parsed = json.loads(_extract_json_object(raw_text))
        if not isinstance(parsed, dict):
            raise ValueError("model response was not a JSON object")
    except (json.JSONDecodeError, ValueError):
        parsed = {}

    out: list[ExtractedField] = []
    for name in EXPECTED_FIELDS:
        entry = parsed.get(name) if isinstance(parsed, dict) else None
        if not isinstance(entry, dict):
            out.append(ExtractedField(field=name, supported=False,
                                      unsupported_reason="model did not propose this field"))
            continue

        value = entry.get("value")
        page = entry.get("page")
        span = entry.get("span")
        page_int = int(page) if isinstance(page, (int, float)) else None

        supported, reason = locate_span(pages, page_int, span if isinstance(span, str) else None)
        out.append(ExtractedField(
            field=name, value=str(value) if value is not None else None,
            page=page_int, span=span if isinstance(span, str) else None,
            supported=supported, unsupported_reason="" if supported else reason,
        ))
    return out


def _extract_json_object(text: str) -> str:
    """Best-effort: pull the first {...} block out of free text. Returns "{}"
    (parses to an empty dict, i.e. every field unsupported) if none found."""
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    return match.group(0) if match else "{}"
