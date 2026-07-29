#!/usr/bin/env python3
"""Schema and hygiene validation for Lamer Konekte AI Instructions v1.

Checks: unique ids, valid JSONL, required fields, valid intents, valid function
names, no secret values, no exact duplicates.

    python scripts/validate_training_dataset.py
Exit code 0 = pass, 1 = fail. Writes training/results/dataset_validation.json.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.prompts.compact_router_v1 import ALLOWED_INTENTS, ROUTABLE_TOOLS  # noqa: E402

DATA = ROOT / "training" / "data"
REQUIRED_FIELDS = [
    "id", "language", "task", "semantic_family", "provenance", "human_review_status",
    "system_prompt_version", "compact_prompt_version", "user_input", "available_tools",
    "expected_intent", "expected_tool_call", "expected_arguments",
    "expected_structured_output", "expected_final_behaviour", "forbidden_behaviour",
    "safety_category", "source_ids", "split",
]
ALLOWED_PROVENANCE = {
    "existing_project_record", "team_authored", "AI_generated_review_required",
    "AI_generated_human_reviewed", "deterministic_template", "official_source_derived",
}
SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"hf_[A-Za-z0-9]{30,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path.name}:{i} invalid JSON — {e}")
    return rows


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    master = load_jsonl(DATA / "master_records.jsonl")
    splits = {name: load_jsonl(DATA / f"{name}.jsonl") for name in ("train", "validation", "test")}

    # unique ids
    ids = Counter(r["id"] for r in master)
    dupes = [i for i, n in ids.items() if n > 1]
    if dupes:
        failures.append(f"duplicate record ids: {dupes[:5]}")

    # required fields
    for r in master:
        missing = [f for f in REQUIRED_FIELDS if f not in r]
        if missing:
            failures.append(f"{r.get('id','?')} missing fields: {missing}")
            break

    # enums and tools
    for r in master:
        if r["expected_intent"] not in ALLOWED_INTENTS:
            failures.append(f"{r['id']} invalid intent {r['expected_intent']!r}")
        tool = r["expected_tool_call"]
        if tool is not None and tool not in ROUTABLE_TOOLS:
            failures.append(f"{r['id']} invalid tool {tool!r}")
        if r["provenance"] not in ALLOWED_PROVENANCE:
            failures.append(f"{r['id']} invalid provenance {r['provenance']!r}")
        if r["split"] not in ("train", "validation", "test"):
            failures.append(f"{r['id']} invalid split {r['split']!r}")

    # no secrets anywhere
    blob = json.dumps(master, ensure_ascii=False)
    for pat in SECRET_PATTERNS:
        if pat.search(blob):
            failures.append(f"possible secret matching {pat.pattern} in dataset")

    # exact duplicate user inputs
    norm = Counter(" ".join(r["user_input"].lower().split()) for r in master)
    exact_dupes = [t for t, n in norm.items() if n > 1]
    if exact_dupes:
        failures.append(f"{len(exact_dupes)} exact duplicate user_input values, e.g. {exact_dupes[:3]}")

    # split files must reconstruct the master exactly
    recombined = sorted(r["id"] for rows in splits.values() for r in rows)
    if recombined != sorted(r["id"] for r in master):
        failures.append("split files do not reconstruct master_records.jsonl")

    # non-empty essentials
    for r in master:
        if not r["user_input"].strip():
            failures.append(f"{r['id']} empty user_input")
        if not r["expected_final_behaviour"].strip():
            warnings.append(f"{r['id']} empty expected_final_behaviour")

    # ratio sanity
    total = len(master)
    ratios = {k: round(100 * len(v) / total, 1) for k, v in splits.items()}
    if not (60 <= ratios["train"] <= 80):
        warnings.append(f"train ratio {ratios['train']}% outside 60-80%")

    report = {
        "total_records": total,
        "semantic_families": len({r["semantic_family"] for r in master}),
        "split_counts": {k: len(v) for k, v in splits.items()},
        "split_ratios_pct": ratios,
        "unique_ids": len(ids),
        "distinct_user_inputs": len(norm),
        "by_provenance": dict(Counter(r["provenance"] for r in master)),
        "by_safety_category": dict(Counter(r["safety_category"] for r in master)),
        "human_review": dict(Counter(r["human_review_status"] for r in master)),
        "failures": failures,
        "warnings": warnings,
        "passed": not failures,
    }
    out = ROOT / "training" / "results" / "dataset_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"records={total} families={report['semantic_families']} splits={report['split_counts']}")
    for w in warnings:
        print(f"  WARN {w}")
    for f in failures:
        print(f"  FAIL {f}")
    print("PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
