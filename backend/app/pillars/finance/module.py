"""BlueFinancePillar — the PillarModule implementation.

Document in, structured findings out. No sensors, no live feed. The model's
ONLY job is to propose field values with a page + supporting quote; this
module's own code (extraction.locate_span, criteria.check_criteria) decides
what is supported and what every criterion's status is. The model is never
asked for, and cannot set, a criteria verdict — see the prompt in
_build_prompt(): it requests field extraction only, no "eligible"/"status" key.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

# Plain `import x.y.z`, not `from x.y import z` — test_pillars_import_boundary
# inspects ast.ImportFrom.module literally, and "app.inference" (the module of
# a from-import) is not itself in ALLOWED_INFERENCE_IMPORTS, only the full
# dotted path is. This form is the one that satisfies the boundary check.
import app.inference.registry as inference_registry

from app.core.config import get_settings
from app.pillars.base import RawBundle, SourceDescriptor
from app.pillars.finance.criteria import check_criteria, load_criteria
from app.pillars.finance.extraction import extract_pdf_pages, fields_from_model_json
from app.pillars.finance.schemas import BlueFinanceResult

SAMPLES_DIR = None  # resolved lazily via get_settings(), see _samples_dir()

SAMPLE_DOCS = {
    "compliant": ("sample_blue_bond_compliant.pdf", "Sample Blue Bond Framework (compliant illustration)"),
    "partial": ("sample_blue_bond_partial.pdf", "Sample Blue Bond Framework (partial illustration)"),
    "ineligible": ("sample_bond_ineligible.pdf", "Sample Corporate Bond Framework (ineligible illustration)"),
}
DEFAULT_SAMPLE = "compliant"


def _samples_dir() -> Path:
    return get_settings().data_dir / "pillars" / "finance" / "samples"


class DocumentNotFound(Exception):
    pass


def _build_prompt(pages: list[str]) -> str:
    numbered = "\n\n".join(f"--- PAGE {i + 1} ---\n{text}" for i, text in enumerate(pages))
    return (
        "You are extracting facts from a bond-framework document. Extract ONLY what is "
        "explicitly stated in the text below. Always respond with the JSON object described "
        "below and nothing else — no prose, no caveats, no markdown fences, even if the "
        "document supports few or none of the fields; an empty or partial JSON object is the "
        "correct response for a document that discloses little, not free text. For each field, if you find supporting text, "
        "return its page number and the EXACT supporting quote (verbatim substring from that "
        "page). If you cannot find explicit support, omit the field entirely rather than "
        "guessing. You are extracting facts only — do not judge eligibility or compliance; "
        "that is decided separately.\n\n"
        "Return ONLY a compact JSON object with this shape (omit any field you cannot support):\n"
        '{"use_of_proceeds_category": {"value": "one of: sustainable_seafood | '
        "coastal_marine_tourism | sustainable_maritime_transport | marine_renewable_energy | "
        'marine_pollution_prevention | sustainable_ports | other", "page": N, "span": "exact quote"},\n'
        ' "evaluation_process_summary": {"value": "...", "page": N, "span": "exact quote"},\n'
        ' "management_of_proceeds_summary": {"value": "...", "page": N, "span": "exact quote"},\n'
        ' "impact_metrics": {"value": "...", "page": N, "span": "exact quote"},\n'
        ' "reporting_commitment": {"value": "...", "page": N, "span": "exact quote"},\n'
        ' "verification_commitment": {"value": "...", "page": N, "span": "exact quote"}}\n\n'
        f"DOCUMENT TEXT:\n{numbered}"
    )


class BlueFinancePillar:
    pillar_id = "finance"
    pillar_name = "Blue Finance"
    result_schema = BlueFinanceResult

    def sources(self) -> list[SourceDescriptor]:
        return [SourceDescriptor(
            name="Uploaded documents", url=None,
            description="User-supplied bond/ESG framework documents; no external feed.",
            status="none",
        )]

    async def fetch(self, params: dict) -> RawBundle:
        """params: {"pdf_bytes": bytes, "document_label": str} for a real upload,
        or {"sample_id": "compliant"|"partial"|"ineligible"} for the committed
        sample corpus. Empty params defaults to the sample corpus (this is what
        the cross-pillar provenance enforcement test in test_provenance_enforcement.py
        exercises with params={})."""
        pdf_bytes = params.get("pdf_bytes")
        if pdf_bytes:
            label = params.get("document_label") or "uploaded document"
            return RawBundle(
                pillar_id=self.pillar_id,
                source=SourceDescriptor(name="Uploaded documents", url=None,
                                        description=label, status="none"),
                retrieved_at=datetime.now(timezone.utc), data_kind="live",
                coverage_note=("User-uploaded document, read in this request only. Extraction covers "
                              "only the six criteria fields below — it is not a full legal or "
                              "financial review of the document."),
                payload={"pdf_bytes": pdf_bytes, "label": label},
            )

        sample_id = params.get("sample_id") or DEFAULT_SAMPLE
        if sample_id not in SAMPLE_DOCS:
            raise DocumentNotFound(f"unknown sample_id {sample_id!r} (known: {sorted(SAMPLE_DOCS)})")
        filename, label = SAMPLE_DOCS[sample_id]
        path = _samples_dir() / filename
        pdf_bytes = path.read_bytes()
        return RawBundle(
            pillar_id=self.pillar_id,
            source=SourceDescriptor(name="Constructed sample corpus", url=None,
                                    description=f"{filename} — fabricated for demo/testing, not a real bond",
                                    status="none"),
            retrieved_at=datetime.now(timezone.utc), data_kind="sample",
            coverage_note=(f"Constructed sample ({label}), not a real bond filing. Demonstrates the "
                          "criteria checker's behaviour; draws no conclusion about any real issuer."),
            payload={"pdf_bytes": pdf_bytes, "label": label},
        )

    async def analyse(self, bundle: RawBundle) -> BlueFinanceResult:
        pages = extract_pdf_pages(bundle.payload["pdf_bytes"])
        label = bundle.payload.get("label", "document")

        provider = inference_registry.get_provider(inference_registry.resolve_name())
        raw_response = provider.chat(_build_prompt(pages), language="en")

        fields = fields_from_model_json(raw_response, pages)
        findings = check_criteria(fields, load_criteria())

        met = sum(1 for f in findings if f.status == "met")
        unmet = sum(1 for f in findings if f.status == "unmet")
        indeterminate = sum(1 for f in findings if f.status == "indeterminate")

        return BlueFinanceResult(
            pillar_id=self.pillar_id, generated_at=datetime.now(timezone.utc),
            provenance={
                "source_name": bundle.source.name, "source_url": bundle.source.url,
                "retrieved_at": bundle.retrieved_at, "data_kind": bundle.data_kind,
                "model_provider": provider.name,
                "coverage_note": bundle.coverage_note,
            },
            document_label=label, fields=fields, findings=findings,
            overall_note=(
                f"{met} of {len(findings)} criteria met, {unmet} unmet, {indeterminate} indeterminate. "
                "This is NOT a pass/fail verdict on the bond — it reports which disclosures were found "
                "and span-verified in the submitted text, nothing more. A human must review the document "
                "itself before relying on any of these findings."
            ),
        )
