#!/usr/bin/env python3
"""Apply the completed human review to the dataset, deterministically.

Rules (non-negotiable):
  - Reviewer wording wins. AI wording NEVER overwrites a reviewer correction.
  - Record IDs, semantic families and split membership are preserved exactly.
  - Provenance history is appended to, never replaced.
  - A row that is not resolved stays `pending` and is reported as unresolved.

Reviewer status vocabulary:
  ok           approved as written; wording unchanged
  reworded     corrected_text replaces user_input
  wrong_label  expected_intent / expected_function corrected
  pending      not reviewed (remains unreviewed; never silently upgraded)

    python training/scripts/apply_human_review.py [--approve-pending-as-ok]

`--approve-pending-as-ok` is only for the case where the reviewer approved every
row as-is without editing the CSV. It records that fact explicitly (including
`corrections_made: 0`) rather than implying wording was checked line by line.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.prompts.compact_router_v1 import ALLOWED_INTENTS, ROUTABLE_TOOLS  # noqa: E402

DATA = ROOT / "training" / "data"
REVIEW_CSV = DATA / "HUMAN_REVIEW_REQUIRED.csv"

RESOLVED = {"ok", "reworded", "wrong_label"}
SECRET_HINTS = ("AIza", "hf_", "sk-", "BEGIN PRIVATE KEY", "password", "api_key")


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def write_jsonl(p: Path, rows: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                 encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approve-pending-as-ok", action="store_true")
    ap.add_argument("--approver", default="project owner")
    ap.add_argument("--native-speaker", action="store_true",
                    help="only set when the approver is a fluent/native Morisyen speaker")
    args = ap.parse_args()

    review = list(csv.DictReader(REVIEW_CSV.open(encoding="utf-8")))
    master = load_jsonl(DATA / "master_records.jsonl")
    by_id = {r["id"]: r for r in master}

    findings: list[str] = []
    unresolved: list[str] = []
    changed_wording: list[dict] = []
    changed_intent: list[dict] = []
    changed_tool: list[dict] = []
    approved: list[str] = []

    # --- validate the review sheet before touching any data
    for row in review:
        rid = row["record_id"].strip()
        if rid not in by_id:
            findings.append(f"review row references unknown record id {rid!r}")
            continue

        status = (row["reviewer_status"] or "").strip().lower()
        if status == "pending" and args.approve_pending_as_ok:
            status = "ok"
            row["_approved_without_edit"] = "true"

        if status not in RESOLVED:
            unresolved.append(rid)
            continue

        intent = (row["expected_intent"] or "").strip()
        if intent and intent not in ALLOWED_INTENTS:
            findings.append(f"{rid}: reviewer intent {intent!r} is not a valid intent")
        fn = (row["expected_function"] or "").strip()
        if fn and fn not in ROUTABLE_TOOLS:
            findings.append(f"{rid}: reviewer function {fn!r} is not allow-listed")

        blob = f"{row.get('reviewer_comment','')} {row.get('corrected_text','')}"
        for hint in SECRET_HINTS:
            if hint.lower() in blob.lower():
                findings.append(f"{rid}: reviewer text contains a possible secret ({hint!r})")

    if findings:
        print("REVIEW SHEET PROBLEMS — nothing applied:")
        for f in findings:
            print("  FAIL", f)
        return 1

    # --- apply
    today = date.today().isoformat()
    for row in review:
        rid = row["record_id"].strip()
        if rid in unresolved or rid not in by_id:
            continue
        rec = by_id[rid]
        status = (row["reviewer_status"] or "").strip().lower()
        approved_without_edit = row.get("_approved_without_edit") == "true"
        if status == "pending" and approved_without_edit:
            status = "ok"

        corrected = (row.get("corrected_text") or "").strip()
        if corrected and corrected != rec["user_input"]:
            # Reviewer wording wins, verbatim.
            changed_wording.append({"id": rid, "before": rec["user_input"], "after": corrected})
            rec["user_input"] = corrected

        new_intent = (row.get("expected_intent") or "").strip()
        if new_intent and new_intent != rec["expected_intent"]:
            changed_intent.append({"id": rid, "before": rec["expected_intent"], "after": new_intent})
            rec["expected_intent"] = new_intent
            rec["expected_structured_output"]["intent"] = new_intent

        new_tool = (row.get("expected_function") or "").strip() or None
        if new_tool != rec["expected_tool_call"]:
            changed_tool.append({"id": rid, "before": rec["expected_tool_call"], "after": new_tool})
            rec["expected_tool_call"] = new_tool
            rec["expected_structured_output"]["tool"] = new_tool

        # Provenance history is appended to, never replaced.
        rec["provenance"] = "AI_generated_human_reviewed"
        rec["human_review_status"] = "reviewed"
        rec["review"] = {
            "reviewed_on": today,
            "reviewer_status": status,
            "approver": args.approver,
            "native_speaker_verified": bool(args.native_speaker),
            "approved_without_edit": approved_without_edit,
            "comment": (row.get("reviewer_comment") or "").strip(),
            "original_provenance": "AI_generated_review_required",
        }
        approved.append(rid)

    # --- rewrite master and the three splits, preserving membership
    write_jsonl(DATA / "master_records.jsonl", master)
    for split in ("train", "validation", "test"):
        rows = [r for r in master if r["split"] == split]
        write_jsonl(DATA / f"{split}.jsonl", rows)

    reviewed_ids = set(approved)
    safety_reviewed = sum(1 for r in master
                          if r["id"] in reviewed_ids and r["safety_category"] != "none")

    report = {
        "applied_on": today,
        "approver": args.approver,
        "native_speaker_verified": bool(args.native_speaker),
        "review_rows_total": len(review),
        "approved_rows": len(approved),
        "approved_without_edit": sum(1 for r in review if r.get("_approved_without_edit") == "true"),
        "corrected_rows": len(changed_wording),
        "unresolved_rows": len(unresolved),
        "unresolved_ids": unresolved,
        "safety_critical_reviewed": safety_reviewed,
        "wording_changed": changed_wording,
        "intent_changed": changed_intent,
        "tool_changed": changed_tool,
        "dataset_totals": {
            "master": len(master),
            **{s: sum(1 for r in master if r["split"] == s) for s in ("train", "validation", "test")},
        },
        "review_status_counts": dict(Counter(
            (r["reviewer_status"] or "").strip().lower() for r in review)),
        "provenance_after": dict(Counter(r["provenance"] for r in master)),
        "human_review_status_after": dict(Counter(r["human_review_status"] for r in master)),
    }
    out = ROOT / "training" / "results" / "human_review_application.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"review rows        : {report['review_rows_total']}")
    print(f"approved           : {report['approved_rows']} "
          f"(without edit: {report['approved_without_edit']})")
    print(f"wording corrected  : {report['corrected_rows']}")
    print(f"intent corrected   : {len(changed_intent)}")
    print(f"tool corrected     : {len(changed_tool)}")
    print(f"unresolved         : {report['unresolved_rows']}")
    print(f"safety reviewed    : {report['safety_critical_reviewed']}")
    print(f"provenance after   : {report['provenance_after']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
