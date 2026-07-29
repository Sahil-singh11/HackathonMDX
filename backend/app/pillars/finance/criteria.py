"""Blue-finance criteria: data, not prompt.

Mirrors app/services/fisheries_rules/engine.py exactly: the model proposes
field VALUES; this module — plain code, no model involved — decides every
criterion's status. A criterion is "met" only when its required field is
code-verified supported (see extraction.py) and, where applicable, its value
matches an allowed set. Anything else is "unmet" or "indeterminate" — never
invented as met from an unsupported or absent field.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.pillars.finance.schemas import CriteriaFinding, ExtractedField


@lru_cache
def load_criteria() -> list[dict]:
    path = get_settings().data_dir / "rules" / "blue_finance_criteria.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["criteria"]


def check_criteria(fields: list[ExtractedField], criteria: list[dict] | None = None) -> list[CriteriaFinding]:
    """Pure function: same inputs always produce the same findings.

    Deliberately takes ExtractedField objects, not raw model output — this
    is the boundary the model's opinion cannot cross. A field's `value` here
    was already code-verified for span support before it reached this
    function (see extraction.locate_span); this function only decides
    what that support means against the criteria.
    """
    rules = criteria if criteria is not None else load_criteria()
    by_field: dict[str, ExtractedField] = {f.field: f for f in fields}
    findings: list[CriteriaFinding] = []

    for rule in rules:
        required = rule["required_field"]
        field = by_field.get(required)
        allowed_values = rule.get("allowed_values")
        advisory_only = bool(rule.get("advisory_only", False))

        if field is None:
            findings.append(CriteriaFinding(
                criterion_id=rule["criterion_id"], label=rule["label"], status="indeterminate",
                evidence=[], note=f"No candidate value was proposed for '{required}'.",
                advisory_only=advisory_only,
            ))
            continue

        if not field.supported:
            findings.append(CriteriaFinding(
                criterion_id=rule["criterion_id"], label=rule["label"], status="unmet",
                evidence=[field],
                note=(field.unsupported_reason or
                      f"'{required}' was proposed but not verified against the source text."),
                advisory_only=advisory_only,
            ))
            continue

        if allowed_values is not None and (field.value or "").strip().lower() not in {
            v.lower() for v in allowed_values
        }:
            findings.append(CriteriaFinding(
                criterion_id=rule["criterion_id"], label=rule["label"], status="indeterminate",
                evidence=[field],
                note=(f"'{field.value}' does not match the corroborated category list — this list is "
                      "not asserted exhaustive (see blue_finance_source_register.json, source F2), so a "
                      "non-match is reported as indeterminate, not a hard fail."),
                advisory_only=advisory_only,
            ))
            continue

        findings.append(CriteriaFinding(
            criterion_id=rule["criterion_id"], label=rule["label"], status="met",
            evidence=[field], note=f"'{required}' is supported by page {field.page} of the source document.",
            advisory_only=advisory_only,
        ))

    return findings
