#!/usr/bin/env python3
"""Semantic-family split integrity.

The rule: every record of one semantic family lives in exactly one split. If a seed's
paraphrases straddle a split boundary, the held-out score is inflated because the model
has already seen the same underlying need.

    python scripts/check_semantic_family_split.py
Exit 0 = pass, 1 = fail. Writes training/results/semantic_split_report.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training" / "data"


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    failures: list[str] = []
    master = load_jsonl(DATA / "master_records.jsonl")

    family_splits: dict[str, set[str]] = defaultdict(set)
    family_sizes: Counter = Counter()
    for r in master:
        family_splits[r["semantic_family"]].add(r["split"])
        family_sizes[r["semantic_family"]] += 1

    straddling = {f: sorted(s) for f, s in family_splits.items() if len(s) > 1}
    for fam, splits in straddling.items():
        failures.append(f"semantic family {fam!r} spans splits {splits}")

    # Each split should see a reasonable spread of groups and intents, otherwise the
    # held-out score measures coverage rather than generalisation.
    by_split_group: dict[str, Counter] = defaultdict(Counter)
    by_split_intent: dict[str, Counter] = defaultdict(Counter)
    for r in master:
        by_split_group[r["split"]][r["group"]] += 1
        by_split_intent[r["split"]][r["expected_intent"]] += 1

    warnings: list[str] = []
    all_intents = {r["expected_intent"] for r in master}
    for split in ("train", "validation", "test"):
        missing = all_intents - set(by_split_intent[split])
        if missing:
            warnings.append(f"split {split} has no records for intent(s) {sorted(missing)}")
    for split in ("train", "test"):
        if "F" not in by_split_group[split]:
            warnings.append(f"split {split} contains no safety (group F) records")

    report = {
        "families": len(family_splits),
        "records": len(master),
        "families_spanning_multiple_splits": straddling,
        "family_size_distribution": dict(Counter(family_sizes.values())),
        "largest_families": family_sizes.most_common(5),
        "by_split_group": {k: dict(v) for k, v in by_split_group.items()},
        "by_split_intent": {k: dict(v) for k, v in by_split_intent.items()},
        "warnings": warnings,
        "failures": failures,
        "passed": not failures,
    }
    out = ROOT / "training" / "results" / "semantic_split_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"families={report['families']} records={report['records']} "
          f"straddling={len(straddling)}")
    for w in warnings:
        print(f"  WARN {w}")
    for f in failures[:10]:
        print(f"  FAIL {f}")
    print("PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
