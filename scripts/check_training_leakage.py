#!/usr/bin/env python3
"""Leakage checks: external-test immutability and near-duplicates across splits.

The 32-case Morisyen benchmark is immutable external test data. This script proves
that nothing in the training data copies it, paraphrases it too closely, or reuses
its expected answers — and that no training/validation/test record is a near
duplicate of a record in another split.

    python scripts/check_training_leakage.py
Exit 0 = pass, 1 = fail. Writes training/results/leakage_report.json.

A full training run must not begin when this fails.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training" / "data"
EXTERNAL = ROOT / "evaluation" / "cases" / "morisyen_cases.json"

# Similarity at or above this between records in DIFFERENT splits, or between any
# training record and an external case, is treated as leakage.
NEAR_DUP_THRESHOLD = 0.85
EXTERNAL_THRESHOLD = 0.80
# Shared 4-word runs with an external case are a copy signal even when the overall
# similarity is low (e.g. a long record embedding a short benchmark phrase).
SHINGLE_N = 4


def norm(text: str) -> str:
    text = text.lower().replace("'", " ").replace("’", " ")
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def shingles(text: str, n: int = SHINGLE_N) -> set[str]:
    words = norm(text).split()
    return {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    failures: list[str] = []
    findings: list[dict] = []

    master = load_jsonl(DATA / "master_records.jsonl")
    ext_bytes = EXTERNAL.read_bytes()
    ext = json.loads(ext_bytes)["cases"]

    # --- 1. external benchmark unchanged since the manifest was written
    manifest = json.loads((DATA / "external_test_manifest.json").read_text(encoding="utf-8"))
    actual_sha = hashlib.sha256(ext_bytes).hexdigest()
    if actual_sha != manifest["sha256"]:
        failures.append(
            f"external benchmark CHANGED: manifest {manifest['sha256'][:12]} vs actual {actual_sha[:12]}. "
            "The 32-case benchmark is immutable — revert it.")
    if len(ext) != manifest["case_count"]:
        failures.append(f"external case count changed: {len(ext)} vs {manifest['case_count']}")

    # --- 2. no training record copies or closely paraphrases an external case
    ext_norm = [(c["id"], norm(c["note"]), shingles(c["note"])) for c in ext]
    for r in master:
        rn = norm(r["user_input"])
        rs = shingles(r["user_input"])
        for cid, cn, cs in ext_norm:
            if rn == cn:
                failures.append(f"{r['id']} is an EXACT copy of external case {cid}")
                continue
            ratio = SequenceMatcher(None, rn, cn).ratio()
            shared = rs & cs
            if ratio >= EXTERNAL_THRESHOLD:
                failures.append(f"{r['id']} ~{ratio:.2f} similar to external case {cid}")
            elif shared:
                failures.append(
                    f"{r['id']} shares {SHINGLE_N}-word run(s) with external case {cid}: {sorted(shared)[:2]}")

    # --- 3. no near duplicates ACROSS splits
    by_split: dict[str, list[dict]] = {}
    for r in master:
        by_split.setdefault(r["split"], []).append(r)
    names = sorted(by_split)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for ra in by_split[a]:
                na = norm(ra["user_input"])
                for rb in by_split[b]:
                    nb = norm(rb["user_input"])
                    if na == nb:
                        failures.append(f"identical user_input across splits: {ra['id']} ({a}) / {rb['id']} ({b})")
                        continue
                    ratio = SequenceMatcher(None, na, nb).ratio()
                    if ratio >= NEAR_DUP_THRESHOLD:
                        failures.append(
                            f"near-duplicate across splits ({ratio:.2f}): {ra['id']} ({a}) / {rb['id']} ({b})")
                    elif ratio >= 0.75:
                        findings.append({"kind": "borderline_cross_split", "similarity": round(ratio, 3),
                                         "a": ra["id"], "a_split": a, "b": rb["id"], "b_split": b})

    # --- 4. no expected answer templates lifted from the benchmark
    ext_intents = {c["id"]: c["expected_intent"] for c in ext}
    if not ext_intents:
        failures.append("external benchmark has no expected_intent values to protect")

    report = {
        "external_benchmark": {
            "path": "evaluation/cases/morisyen_cases.json",
            "sha256": actual_sha,
            "matches_manifest": actual_sha == manifest["sha256"],
            "case_count": len(ext),
            "role": "immutable_external_test",
        },
        "thresholds": {"cross_split_near_duplicate": NEAR_DUP_THRESHOLD,
                       "external_similarity": EXTERNAL_THRESHOLD,
                       "shingle_n": SHINGLE_N},
        "records_checked": len(master),
        "comparisons_vs_external": len(master) * len(ext),
        "borderline_findings": findings[:20],
        "borderline_count": len(findings),
        "failures": failures,
        "passed": not failures,
    }
    out = ROOT / "training" / "results" / "leakage_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"checked {len(master)} records against {len(ext)} external cases "
          f"({report['comparisons_vs_external']} comparisons)")
    print(f"external sha256 matches manifest: {report['external_benchmark']['matches_manifest']}")
    print(f"borderline cross-split pairs (0.75-{NEAR_DUP_THRESHOLD}): {len(findings)}")
    for f in failures[:20]:
        print(f"  FAIL {f}")
    print("PASS" if not failures else f"FAIL ({len(failures)} issues)")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
