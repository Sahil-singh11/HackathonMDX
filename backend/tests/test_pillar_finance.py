"""Task 6b — Blue Finance pillar.

Default suite runs entirely under PROVIDER_MODE=mock (conftest.py) and the
autouse socket guard — every test here is offline by construction, not by
special-casing. The pillar's own MockProvider path is exercised directly;
no test flips settings to hit a real model.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.pillars.finance.criteria import check_criteria, load_criteria
from app.pillars.finance.extraction import extract_pdf_pages, fields_from_model_json, locate_span
from app.pillars.finance.module import BlueFinancePillar, DocumentNotFound
from app.pillars.finance.schemas import ExtractedField


def _run(coro):
    return asyncio.run(coro)


def _sample_bytes(name: str) -> bytes:
    path = get_settings().data_dir / "pillars" / "finance" / "samples" / name
    return path.read_bytes()


# -- 1. criteria check is deterministic and model-independent ---------------

def test_check_criteria_is_pure_and_needs_no_model():
    criteria = load_criteria()
    fields = [
        ExtractedField(field="use_of_proceeds_category", value="sustainable_seafood",
                       page=1, span="sustainable seafood", supported=True),
        ExtractedField(field="evaluation_process_summary", value="committee review",
                       page=1, span="committee", supported=True),
        ExtractedField(field="management_of_proceeds_summary", supported=False,
                       unsupported_reason="not proposed"),
        ExtractedField(field="impact_metrics", supported=False, unsupported_reason="not proposed"),
        ExtractedField(field="reporting_commitment", value="annual report",
                       page=2, span="annual report", supported=True),
        ExtractedField(field="verification_commitment", supported=False, unsupported_reason="not proposed"),
    ]
    findings = check_criteria(fields, criteria)
    by_id = {f.criterion_id: f for f in findings}

    assert by_id["use_of_proceeds_disclosed"].status == "met"
    assert by_id["use_of_proceeds_blue_eligible"].status == "met"
    assert by_id["evaluation_process_disclosed"].status == "met"
    assert by_id["management_of_proceeds_disclosed"].status == "unmet"
    assert by_id["impact_metrics_disclosed"].status == "unmet"
    assert by_id["reporting_commitment_disclosed"].status == "met"
    assert by_id["verification_commitment_disclosed"].status == "unmet"
    assert by_id["verification_commitment_disclosed"].advisory_only is True


def test_check_criteria_reports_indeterminate_for_unknown_category():
    fields = [ExtractedField(field="use_of_proceeds_category", value="deep_sea_mining",
                             page=1, span="deep sea mining", supported=True)]
    findings = check_criteria(fields, load_criteria())
    by_id = {f.criterion_id: f for f in findings}
    assert by_id["use_of_proceeds_blue_eligible"].status == "indeterminate"
    assert "not asserted exhaustive" in by_id["use_of_proceeds_blue_eligible"].note


def test_check_criteria_never_trusts_unsupported_field_even_with_a_value():
    """A field can carry a plausible-looking value and still be unmet if the
    code could not verify it — this is the whole point of span verification."""
    fields = [ExtractedField(field="use_of_proceeds_category", value="sustainable_seafood",
                             page=1, span=None, supported=False,
                             unsupported_reason="model gave no supporting span")]
    findings = check_criteria(fields, load_criteria())
    by_id = {f.criterion_id: f for f in findings}
    assert by_id["use_of_proceeds_disclosed"].status == "unmet"


# -- 2. every extracted field carries a span or is marked unsupported -------

def test_locate_span_confirms_real_text():
    pages = ["The issuer commits to an annual impact report covering all eligible projects."]
    ok, reason = locate_span(pages, 1, "annual impact report")
    assert ok and reason == ""


def test_locate_span_rejects_text_not_present():
    pages = ["Some unrelated content about corporate governance."]
    ok, reason = locate_span(pages, 1, "annual impact report")
    assert not ok and "not found" in reason


def test_locate_span_rejects_out_of_range_page():
    ok, reason = locate_span(["only one page"], 5, "anything")
    assert not ok and "out of range" in reason


def test_locate_span_rejects_missing_span_or_page():
    assert locate_span(["text"], 1, None)[0] is False
    assert locate_span(["text"], None, "text")[0] is False


def test_fields_from_model_json_marks_unsupported_when_span_does_not_match():
    pages = ["This page discusses office renovations and staff parking."]
    raw = ('{"use_of_proceeds_category": {"value": "sustainable_seafood", "page": 1, '
          '"span": "sustainable seafood aquaculture projects"}}')
    fields = fields_from_model_json(raw, pages)
    by_name = {f.field: f for f in fields}
    assert by_name["use_of_proceeds_category"].supported is False


def test_fields_from_model_json_handles_unparseable_response_without_crashing():
    fields = fields_from_model_json("I cannot help with that request.", ["some page text"])
    assert len(fields) == 6
    assert all(not f.supported for f in fields)


# -- 3. a test proving the model output cannot set a criteria verdict --------

def test_model_cannot_smuggle_a_verdict_into_the_result():
    """Even if a (mis)generation includes extra keys claiming everything is
    fine, fields_from_model_json only ever reads the six known field names —
    any 'status'/'verdict' key the model invents is silently discarded, and
    check_criteria() computes its own status from span-verified fields only."""
    pages = ["This document contains no relevant disclosures whatsoever."]
    raw = ('{"status": "all criteria met", "verdict": "eligible", "eligible": true, '
          '"use_of_proceeds_category": {"value": "sustainable_seafood", "page": 1, '
          '"span": "text that does not appear on the page"}}')
    fields = fields_from_model_json(raw, pages)
    findings = check_criteria(fields, load_criteria())
    assert all(f.status != "met" for f in findings), (
        "the model's invented 'status'/'verdict'/'eligible' keys must have no effect "
        "on the computed findings"
    )


# -- 4. provenance correctness + zero network calls (via the real mock path) -

def test_fetch_sample_has_sample_provenance():
    pillar = BlueFinancePillar()
    bundle = _run(pillar.fetch({"sample_id": "compliant"}))
    assert bundle.data_kind == "sample"
    assert "not a real bond" in bundle.source.description.lower()


def test_fetch_uploaded_document_has_live_provenance():
    pillar = BlueFinancePillar()
    bundle = _run(pillar.fetch({"pdf_bytes": _sample_bytes("sample_blue_bond_compliant.pdf"),
                                "document_label": "test upload"}))
    assert bundle.data_kind == "live"


def test_fetch_unknown_sample_id_raises():
    pillar = BlueFinancePillar()
    with pytest.raises(DocumentNotFound):
        _run(pillar.fetch({"sample_id": "does-not-exist"}))


def test_fetch_with_empty_params_defaults_to_a_sample():
    """Exercises the same params={} path test_provenance_enforcement.py's
    cross-pillar contract test uses."""
    pillar = BlueFinancePillar()
    bundle = _run(pillar.fetch({}))
    assert bundle.data_kind == "sample"


def test_analyse_end_to_end_on_compliant_sample_never_crashes_and_carries_provenance():
    pillar = BlueFinancePillar()
    bundle = _run(pillar.fetch({"sample_id": "compliant"}))
    result = _run(pillar.analyse(bundle))

    assert result.pillar_id == "finance"
    assert result.provenance.model_provider  # non-empty, matches whatever the mock env resolves to
    assert result.provenance.data_kind == "sample"
    assert len(result.findings) == len(load_criteria())
    assert "not a pass/fail verdict" in result.overall_note.lower()


def test_analyse_on_all_three_samples_produces_a_result_and_never_claims_legality():
    pillar = BlueFinancePillar()
    for sample_id in ("compliant", "partial", "ineligible"):
        bundle = _run(pillar.fetch({"sample_id": sample_id}))
        result = _run(pillar.analyse(bundle))
        assert result.findings
        assert "verdict" not in result.overall_note.lower() or "not a pass/fail verdict" in result.overall_note.lower()


# -- 5. real PDF text extraction ---------------------------------------------

def test_extract_pdf_pages_reads_real_generated_samples():
    pages = extract_pdf_pages(_sample_bytes("sample_blue_bond_compliant.pdf"))
    assert len(pages) >= 1
    assert "CONSTRUCTED SAMPLE" in pages[0]
    assert "sustainable seafood" in pages[0].lower()


# -- 6. full route stack: mount, enable-gate, endpoints ----------------------

def test_route_honours_a_non_default_sample_id():
    """Regression test for a real bug found in review: sample_id was a bare
    function parameter, not Form(...), alongside an UploadFile sibling — so
    FastAPI silently failed to bind it from multipart data and fetch() always
    fell through to DEFAULT_SAMPLE ("compliant"). Requesting "compliant"
    itself could never have caught this, since that value IS the buggy
    fallback's default — this test deliberately requests a DIFFERENT sample
    and checks the response actually reflects it."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.ratelimit import InMemoryRateLimiter
    from app.pillars.finance.module import DEFAULT_SAMPLE, SAMPLE_DOCS
    from app.pillars.finance.routes import router as finance_router
    from app.pillars.registry import PillarDescriptor, PillarRegistry
    from app.pillars.routes import build_pillar_router

    reg = PillarRegistry(enabled_ids=lambda: {"finance"})
    reg.register_descriptor(PillarDescriptor(pillar_id="finance", pillar_name="Blue Finance"))
    reg.register_module(BlueFinancePillar(), router=finance_router)
    app = FastAPI()
    app.include_router(build_pillar_router(registry=reg, limiter=InMemoryRateLimiter(limit=30, window_seconds=60.0)))
    client = TestClient(app)

    non_default = next(sid for sid in SAMPLE_DOCS if sid != DEFAULT_SAMPLE)
    r = client.post("/api/pillars/finance/analyse", data={"sample_id": non_default})
    assert r.status_code == 200
    assert SAMPLE_DOCS[non_default][1] in r.json()["document_label"]


def test_finance_routes_serve_when_enabled_on_an_isolated_app():
    """Same isolated-registry pattern as test_pillar_contract.py's dummy-pillar
    tests, but mounting the REAL finance router — proves criteria/samples/
    analyse all serve once enabled, without touching the app-wide singleton."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.ratelimit import InMemoryRateLimiter
    from app.pillars.finance.routes import router as finance_router
    from app.pillars.registry import PillarDescriptor, PillarRegistry
    from app.pillars.routes import build_pillar_router

    reg = PillarRegistry(enabled_ids=lambda: {"finance"})
    reg.register_descriptor(PillarDescriptor(pillar_id="finance", pillar_name="Blue Finance"))
    reg.register_module(BlueFinancePillar(), router=finance_router)
    app = FastAPI()
    app.include_router(build_pillar_router(registry=reg, limiter=InMemoryRateLimiter(limit=30, window_seconds=60.0)))
    client = TestClient(app)

    assert client.get("/api/pillars/finance/criteria").status_code == 200
    assert len(client.get("/api/pillars/finance/samples").json()["samples"]) == 3

    r = client.post("/api/pillars/finance/analyse", data={"sample_id": "compliant"})
    assert r.status_code == 200
    body = r.json()
    assert body["pillar_id"] == "finance"
    assert body["provenance"]["data_kind"] == "sample"
    assert len(body["findings"]) == len(load_criteria())


def test_finance_provenance_probe_is_cheap_and_never_claims_inference():
    """/provenance runs fetch() only (no PDF text extraction, no model call), same
    convention as tourism/energy (see test_pillar_probe.py) — filling a gap the
    /pillars index previously rendered as "not reported" for finance specifically."""
    import time

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.ratelimit import InMemoryRateLimiter
    from app.pillars.finance.routes import router as finance_router
    from app.pillars.probe import NOT_INVOKED
    from app.pillars.registry import PillarDescriptor, PillarRegistry
    from app.pillars.routes import build_pillar_router

    reg = PillarRegistry(enabled_ids=lambda: {"finance"})
    reg.register_descriptor(PillarDescriptor(pillar_id="finance", pillar_name="Blue Finance"))
    reg.register_module(BlueFinancePillar(), router=finance_router)
    app = FastAPI()
    app.include_router(build_pillar_router(registry=reg, limiter=InMemoryRateLimiter(limit=30, window_seconds=60.0)))
    client = TestClient(app)

    start = time.monotonic()
    r = client.get("/api/pillars/finance/provenance")
    elapsed = time.monotonic() - start

    assert r.status_code == 200
    body = r.json()
    assert body["pillar_id"] == "finance"
    assert body["probe"] is True
    assert body["provenance"]["data_kind"] == "sample"  # no upload -> default sample corpus
    assert body["provenance"]["model_provider"] == NOT_INVOKED
    assert elapsed < 5.0, f"probe took {elapsed:.2f}s — has a model call crept in?"
