#!/usr/bin/env python3
"""Safety validation of the training corpus.

Training data teaches behaviour, so an unsafe *target* is worse than an unsafe model
output. This checks that nothing in the dataset teaches the model to:

  - state or invent a fisheries rule, closed season or minimum size;
  - declare a catch legal or illegal;
  - guarantee marine safety;
  - claim an authoritative species identification;
  - treat a photo-judged size as a measurement;
  - present the mock ministry endpoint as official;
  - call a function outside the allow-list.

It also confirms every safety-category record carries an explicit forbidden_behaviour,
and that safety-critical wording is not trained as authoritative while still unreviewed.

    python scripts/check_training_safety.py
Exit 0 = pass, 1 = fail. Writes training/results/safety_validation.json.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.prompts.compact_router_v1 import ROUTABLE_TOOLS  # noqa: E402

DATA = ROOT / "training" / "data"

# Patterns that must never appear in an EXPECTED behaviour (what we teach the model to do).
# Phrased to catch assertions, not prohibitions — "never say it is legal" is fine.
UNSAFE_TARGET = [
    (re.compile(r"\b(it is|this is|the catch is)\s+(legal|illegal)\b", re.I), "legal_verdict"),
    (re.compile(r"\bminimum (legal )?size is\s*\d", re.I), "invented_minimum_size"),
    (re.compile(r"\bclosed season (is|runs|starts)\b", re.I), "invented_closed_season"),
    (re.compile(r"\b(safe to (sail|go out|fish)|conditions are safe|guaranteed safe)\b", re.I), "safety_guarantee"),
    (re.compile(r"\b(definitely|certainly) (a|an|the)\b", re.I), "authoritative_identification"),
    (re.compile(r"\bconfirmed (as|to be) (a|an|the)\b", re.I), "authoritative_identification"),
    (re.compile(r"\bofficial(ly)? submitted to the (ministry|government)\b", re.I), "fake_official_submission"),
    (re.compile(r"\bmeasured length from the (photo|image)\b", re.I), "visual_size_as_measurement"),
]

# Every safety-category record must forbid something explicitly.
SAFETY_CATEGORIES_REQUIRING_FORBIDDEN = {
    "marine_safety_guarantee", "invented_regulation", "bypass_confirmation",
    "visual_size_as_measurement", "unknown_function_request", "prompt_injection",
    "secret_request", "fake_official_submission", "legal_decision_request",
    "false_certainty_pressure", "privacy_request",
}


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    master = load_jsonl(DATA / "master_records.jsonl")

    for r in master:
        target_text = " ".join([
            r["expected_final_behaviour"],
            json.dumps(r["expected_structured_output"], ensure_ascii=False),
        ])
        for pat, label in UNSAFE_TARGET:
            if pat.search(target_text):
                failures.append(f"{r['id']} teaches unsafe target ({label}): {pat.pattern}")

        # allow-list enforcement
        tool = r["expected_tool_call"]
        if tool is not None and tool not in ROUTABLE_TOOLS:
            failures.append(f"{r['id']} targets non-allow-listed tool {tool!r}")

        # safety records must state what is forbidden
        if r["safety_category"] in SAFETY_CATEGORIES_REQUIRING_FORBIDDEN and not r["forbidden_behaviour"]:
            failures.append(f"{r['id']} has safety_category {r['safety_category']!r} but no forbidden_behaviour")

        # unknown-function requests must not select a tool
        if r["safety_category"] == "unknown_function_request" and tool is not None:
            failures.append(f"{r['id']} is an unknown-function request but selects tool {tool!r}")

        # invariants must never be taught as lowerable
        so = r["expected_structured_output"]
        if so.get("species_confirmation_required") is not True:
            failures.append(f"{r['id']} does not require species confirmation")
        if so.get("measured_size_required") is not True:
            failures.append(f"{r['id']} does not require a measured size")

        # safety-critical wording must be reviewed before it is trained as authoritative
        if r["safety_category"] != "none" and r["human_review_status"] == "pending":
            warnings.append(f"{r['id']} is safety-critical and still unreviewed "
                            f"({r['provenance']})")

    # the mock declaration must always be labelled
    mock_records = [r for r in master if r["expected_tool_call"] == "submit_mock_declaration"]
    for r in mock_records:
        blob = " ".join(r["forbidden_behaviour"]) + r["expected_final_behaviour"]
        if "mock" not in blob.lower():
            failures.append(f"{r['id']} uses submit_mock_declaration without labelling it a mock")

    safety_records = [r for r in master if r["safety_category"] != "none"]
    unreviewed_safety = [r for r in safety_records if r["human_review_status"] == "pending"]

    report = {
        "records": len(master),
        "safety_records": len(safety_records),
        "safety_records_unreviewed": len(unreviewed_safety),
        "by_safety_category": dict(Counter(r["safety_category"] for r in master)),
        "mock_declaration_records": len(mock_records),
        "unsafe_target_patterns_checked": len(UNSAFE_TARGET),
        "warnings": warnings,
        "failures": failures,
        "passed": not failures,
        "note": ("Warnings list safety-critical records whose Morisyen wording is AI-generated and "
                 "not yet native-speaker reviewed. They are marked in the dataset and must be "
                 "reported separately in final metrics."),
    }
    out = ROOT / "training" / "results" / "safety_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"safety records={len(safety_records)} unreviewed={len(unreviewed_safety)} "
          f"patterns={len(UNSAFE_TARGET)}")
    for w in warnings[:5]:
        print(f"  WARN {w}")
    if len(warnings) > 5:
        print(f"  WARN ... and {len(warnings) - 5} more unreviewed safety records")
    for f in failures[:15]:
        print(f"  FAIL {f}")
    print("PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
