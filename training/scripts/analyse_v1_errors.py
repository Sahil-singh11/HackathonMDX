#!/usr/bin/env python3
"""Targeted error analysis of the v1 tuned adapter.

Reads the frozen v1 predictions and produces the artifacts that tell dataset v2 what to
fix. Held-out labels are treated as ground truth throughout: a disagreement is a model
error or an annotation *concern*, never a licence to relabel the test set.

    python training/scripts/analyse_v1_errors.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.prompts.compact_router_v1 import ALLOWED_INTENTS  # noqa: E402

ARCHIVE = ROOT / "training" / "archive" / "v1"
RESULTS = ROOT / "training" / "results"
INTENTS = list(ALLOWED_INTENTS)


def main() -> int:
    comparison = list(csv.DictReader((ARCHIVE / "e2b_comparison.csv").open(encoding="utf-8")))
    master = {json.loads(l)["id"]: json.loads(l)
              for l in (ARCHIVE / "master_records.jsonl").read_text(encoding="utf-8").splitlines()
              if l.strip()}
    metrics = json.loads((ARCHIVE / "evaluation_metrics.json").read_text(encoding="utf-8"))

    def norm(v: str | None) -> str:
        v = (v or "").strip()
        return v if v else "(none)"

    # ---------------- confusion matrix (tuned)
    conf: dict[str, Counter] = defaultdict(Counter)
    for r in comparison:
        conf[r["expected_intent"]][norm(r.get("pred_intent_tuned"))] += 1

    pred_labels = sorted({p for c in conf.values() for p in c})
    with (RESULTS / "v1_confusion_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["expected \\ predicted", *pred_labels, "support"])
        for exp in INTENTS:
            row = [exp] + [conf[exp][p] for p in pred_labels] + [sum(conf[exp].values())]
            w.writerow(row)

    # ---------------- per-intent metrics
    per_intent = []
    for it in INTENTS:
        tp = conf[it][it]
        support = sum(conf[it].values())
        predicted = sum(conf[e][it] for e in conf)
        fn = support - tp
        fp = predicted - tp
        prec = tp / predicted if predicted else 0.0
        rec = tp / support if support else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        top_conf = [(p, n) for p, n in conf[it].most_common() if p != it and n]
        per_intent.append({
            "intent": it, "support": support, "true_positive": tp,
            "false_negative": fn, "false_positive": fp,
            "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
            "most_confused_with": top_conf[0][0] if top_conf else "",
            "most_confused_count": top_conf[0][1] if top_conf else 0,
        })
    with (RESULTS / "v1_per_intent_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(per_intent[0]))
        w.writeheader()
        w.writerows(per_intent)

    # ---------------- tool / argument errors
    arg_rows = []
    for r in comparison:
        rid = r["id"]
        rec = master.get(rid, {})
        exp_tool = norm(r.get("pred_tool_untuned") and None) if False else norm(rec.get("expected_tool_call"))
        got_tool = norm(r.get("pred_tool_tuned"))
        intent_ok = r.get("intent_ok_tuned", "").strip().lower() == "true"
        tool_ok = r.get("tool_ok_tuned", "").strip().lower() == "true"
        if tool_ok:
            continue
        if got_tool == "(none)" and exp_tool != "(none)":
            kind = "missing_tool"
        elif got_tool != "(none)" and exp_tool == "(none)":
            kind = "invented_tool"
        else:
            kind = "wrong_tool"
        arg_rows.append({
            "id": rid, "group": rec.get("group", ""), "task": rec.get("task", ""),
            "language": rec.get("language", ""),
            "expected_intent": rec.get("expected_intent", ""),
            "predicted_intent": norm(r.get("pred_intent_tuned")),
            "intent_correct": intent_ok,
            "expected_tool": exp_tool, "predicted_tool": got_tool,
            "error_kind": ("correct_intent_wrong_tool" if intent_ok else "wrong_intent_and_tool"),
            "tool_error_type": kind,
            "expected_arguments": json.dumps(rec.get("expected_arguments", {}), ensure_ascii=False),
        })
    with (RESULTS / "v1_argument_errors.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(arg_rows[0]) if arg_rows else ["id"])
        w.writeheader()
        w.writerows(arg_rows)

    # ---------------- declaration-specific errors
    decl_rows = []
    for r in comparison:
        rec = master.get(r["id"], {})
        exp, got = rec.get("expected_intent"), norm(r.get("pred_intent_tuned"))
        if exp != "make_declaration" and got != "make_declaration":
            continue
        decl_rows.append({
            "id": r["id"], "semantic_family": rec.get("semantic_family", ""),
            "language": rec.get("language", ""),
            "user_input": rec.get("user_input", ""),
            "expected_intent": exp, "predicted_intent": got,
            "correct": exp == got,
            "direction": ("missed_declaration" if exp == "make_declaration" and got != exp
                          else "over_predicted_declaration" if exp != "make_declaration" else "correct"),
            "expected_tool": norm(rec.get("expected_tool_call")),
            "predicted_tool": norm(r.get("pred_tool_tuned")),
            "prepare_vs_submit": ("prepare" if rec.get("expected_tool_call") == "prepare_catch_declaration"
                                  else "submit" if rec.get("expected_tool_call") == "submit_mock_declaration"
                                  else "other"),
        })
    with (RESULTS / "v1_declaration_errors.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(decl_rows[0]) if decl_rows else ["id"])
        w.writeheader()
        w.writerows(decl_rows)

    summary = {
        "source": "training/archive/v1 (frozen Step-3 artifacts)",
        "internal_test_records": len(comparison),
        "one_record_worth_pp": round(100 / len(comparison), 2),
        "tuned_internal": {k: v for k, v in (metrics.get("tuned_internal") or {}).items()
                           if k != "per_intent_f1"},
        "tuned_external_intent_accuracy": (metrics.get("tuned_external") or {}).get("intent_accuracy"),
        "per_intent": per_intent,
        "tool_errors": len(arg_rows),
        "tool_error_breakdown": dict(Counter(r["tool_error_type"] for r in arg_rows)),
        "intent_correct_but_tool_wrong": sum(1 for r in arg_rows if r["intent_correct"]),
        "declaration_rows": len(decl_rows),
        "declaration_missed": sum(1 for r in decl_rows if r["direction"] == "missed_declaration"),
        "declaration_over_predicted": sum(1 for r in decl_rows if r["direction"] == "over_predicted_declaration"),
    }
    (RESULTS / "v1_error_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")

    print(json.dumps({k: v for k, v in summary.items() if k != "per_intent"}, indent=2))
    print("\nper-intent:")
    for p in per_intent:
        print(f"  {p['intent']:18} P={p['precision']:.3f} R={p['recall']:.3f} F1={p['f1']:.3f} "
              f"support={p['support']:>2}  confused_with={p['most_confused_with']}({p['most_confused_count']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
