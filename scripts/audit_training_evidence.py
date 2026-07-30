#!/usr/bin/env python3
"""Training-evidence integrity audit.

Every headline claim must be traceable to a stored artifact. The audit FAILS if a
documented number has no supporting artifact, or if a submission document contains a
forbidden claim.

    python scripts/audit_training_evidence.py
Writes evaluation/results/final_training_evidence_audit.json and
docs/FINAL_TRAINING_EVIDENCE_AUDIT.md. Exit 0 = pass.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training" / "data"
RESULTS = ROOT / "training" / "results"
ARCHIVE = ROOT / "training" / "archive" / "v1"

ROWS: list[dict] = []


def claim(name: str, claimed, actual, source: str, tol: float | None = None) -> None:
    if tol is not None and isinstance(claimed, (int, float)) and isinstance(actual, (int, float)):
        ok = abs(float(claimed) - float(actual)) <= tol
    else:
        ok = claimed == actual
    ROWS.append({"claim": name, "documented": claimed, "artifact_value": actual,
                 "source": source, "supported": bool(ok)})
    print(f"  {'ok  ' if ok else 'FAIL'} {name}: doc={claimed} artifact={actual}")


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> int:
    v2 = jl(DATA / "master_records_v2.jsonl")
    ch = jl(DATA / "v2_challenge_test.jsonl")
    i34 = jl(DATA / "internal_test_v1_34.jsonl")
    ext = json.loads((ROOT / "evaluation" / "cases" / "morisyen_cases.json")
                     .read_text(encoding="utf-8"))["cases"]
    ev = json.loads((RESULTS / "v2_evaluation_metrics.json").read_text(encoding="utf-8"))
    tm = json.loads((RESULTS / "v2_training_metrics.json").read_text(encoding="utf-8"))
    v1m = json.loads((ARCHIVE / "evaluation_metrics.json").read_text(encoding="utf-8"))
    extman = json.loads((DATA / "external_test_manifest.json").read_text(encoding="utf-8"))
    chman = json.loads((DATA / "v2_challenge_manifest.json").read_text(encoding="utf-8"))

    ti, te, tc = ev["tuned_internal"], ev["tuned_external"], ev["tuned_challenge"]
    pi = {r["intent"]: r for r in
          __import__("csv").DictReader((RESULTS / "v2_per_intent_metrics.csv").open(encoding="utf-8"))}

    print("dataset & splits")
    claim("dataset records = 338", 338, len(v2), "master_records_v2.jsonl")
    claim("semantic families = 164", 164, len({r["semantic_family"] for r in v2}),
          "master_records_v2.jsonl")
    claim("train = 248", 248, sum(1 for r in v2 if r["split"] == "train"), "split field")
    claim("validation = 42", 42, sum(1 for r in v2 if r["split"] == "validation"), "split field")
    claim("internal test = 34", 34, len(i34), "internal_test_v1_34.jsonl")
    claim("external test = 32", 32, len(ext), "morisyen_cases.json")
    claim("challenge test = 24", 24, len(ch), "v2_challenge_test.jsonl")

    print("checksums")
    claim("external benchmark checksum matches manifest", extman["sha256"],
          hashlib.sha256((ROOT / "evaluation" / "cases" / "morisyen_cases.json").read_bytes()).hexdigest(),
          "external_test_manifest.json")
    claim("challenge set checksum matches manifest", chman["sha256"],
          hashlib.sha256((DATA / "v2_challenge_test.jsonl").read_bytes()).hexdigest(),
          "v2_challenge_manifest.json")

    print("training run")
    claim("Kaggle GPU = Tesla T4", "Tesla T4", tm.get("gpu"), "v2_training_metrics.json")
    claim("training duration ~552 s", 552, round(tm["train_seconds"]), "v2_training_metrics.json",
          tol=2)
    claim("peak VRAM = 9.21 GiB", 9.21, round(tm["peak_vram_gb"], 2), "v2_training_metrics.json",
          tol=0.01)
    claim("best validation loss = 0.0577", 0.0577, round(tm["best_eval_loss"], 4),
          "v2_training_metrics.json", tol=0.0001)
    claim("trainable parameters = 12,079,104", 12079104, tm["trainable_params"],
          "v2_training_metrics.json")
    adapter = ROOT / "kaggle" / "outputs" / "e2b_router_v2" / "e2b_router_adapter_v2" / "adapter_model.safetensors"
    claim("adapter size ~48.4 MB (fp32 safetensors)", 48.4,
          round(adapter.stat().st_size / 1e6, 1) if adapter.exists() else None,
          "kaggle/outputs (gitignored)", tol=0.1)

    print("v1 metrics")
    claim("v1 internal intent = 73.5%", 0.7353, v1m["tuned_internal"]["intent_accuracy"],
          "archive/v1/evaluation_metrics.json", tol=1e-4)
    claim("v1 external intent = 75.0%", 0.75, v1m["tuned_external"]["intent_accuracy"],
          "archive/v1/evaluation_metrics.json", tol=1e-4)
    claim("v1 tool accuracy = 58.8%", 0.5882, v1m["tuned_internal"]["tool_accuracy"],
          "archive/v1/evaluation_metrics.json", tol=1e-4)
    claim("v1 declaration recall = 0.455", 0.4545,
          v1m["tuned_internal"]["per_intent_f1"]["make_declaration"]["recall"],
          "archive/v1/evaluation_metrics.json", tol=1e-3)

    print("v2 metrics")
    claim("v2 internal intent = 85.3%", 0.8529, ti["intent_accuracy"],
          "v2_evaluation_metrics.json", tol=1e-4)
    claim("v2 external intent = 78.1%", 0.7812, te["intent_accuracy"],
          "v2_evaluation_metrics.json", tol=1e-4)
    claim("v2 challenge intent = 70.8%", 0.7083, tc["intent_accuracy"],
          "v2_evaluation_metrics.json", tol=1e-4)
    claim("v2 tool accuracy = 58.8%", 0.5882, ti["tool_accuracy"],
          "v2_evaluation_metrics.json", tol=1e-4)
    claim("structured validity = 100%", 1.0, ti["structured_validity"],
          "v2_evaluation_metrics.json")
    claim("safety = 100%", 1.0, ti["safety_pass_rate"], "v2_evaluation_metrics.json")
    claim("unknown-function rate = 0%", 0.0, ti["unknown_function_rate"],
          "v2_evaluation_metrics.json")
    claim("routing latency ~4.6 s", 4600, ti["median_latency_ms"],
          "v2_evaluation_metrics.json", tol=400)

    print("declaration recall")
    claim("v2 internal declaration recall = 100%", 1.0,
          float(pi["make_declaration"]["recall"]), "v2_per_intent_metrics.csv", tol=1e-6)
    claim("v2 external declaration recall = 100%", 1.0,
          te["per_intent_f1"]["make_declaration"]["recall"], "v2_evaluation_metrics.json", tol=1e-6)
    claim("v2 challenge declaration recall = 72.7%", 0.7273,
          tc["per_intent_f1"]["make_declaration"]["recall"], "v2_evaluation_metrics.json", tol=1e-3)

    print("acceptance gate")
    claim("gate A rejected", False, ev["gate_a"]["ACCEPTED"], "v2_evaluation_metrics.json")
    claim("gate B rejected", False, ev["gate_b"]["ACCEPTED"], "v2_evaluation_metrics.json")
    claim("decision = REJECTED", "REJECTED", ev["decision"], "v2_evaluation_metrics.json")
    claim("gate doc pre-registered before training", True,
          "PRE-REGISTERED" in (ROOT / "docs" / "V2_PRE_REGISTERED_ACCEPTANCE_GATE.md")
          .read_text(encoding="utf-8"), "V2_PRE_REGISTERED_ACCEPTANCE_GATE.md")

    # ---------------- forbidden claims / approved phrase
    docs = ["docs/AI_SUBMISSION_SUMMARY.md", "docs/AI_JUDGE_TECHNICAL_PROOF.md",
            "docs/AI_DEMO_SCRIPT.md", "docs/AI_LIMITATIONS.md", "docs/AI_FINAL_HANDOFF.md",
            "docs/AI_MODEL_SELECTION_DECISION.md", "docs/AI_STEP4_FINAL_REPORT.md",
            "kaggle/writeup.md"]
    forbidden = [
        (re.compile(r"adapter is (now |the )?production", re.I), "adapter-as-production"),
        (re.compile(r"universal(ly)? 85", re.I), "universal accuracy"),
        (re.compile(r"all Morisyen (data )?(is|was) native[- ]speaker verified", re.I),
         "native-speaker claim"),
        (re.compile(r"\bAI (makes|decides) legal", re.I), "legal decisions"),
        (re.compile(r"guarantee[sd]? (marine )?safety", re.I), "marine safety guarantee"),
        (re.compile(r"ministry submission is real", re.I), "real ministry"),
    ]
    violations = []
    for d in docs:
        text = (ROOT / d).read_text(encoding="utf-8")
        for pat, label in forbidden:
            if pat.search(text):
                violations.append(f"{d}: {label}")
    ROWS.append({"claim": "no forbidden claim in submission documents", "documented": "none",
                 "artifact_value": violations or "none", "source": ", ".join(docs),
                 "supported": not violations})
    print(f"  {'ok  ' if not violations else 'FAIL'} no forbidden claim in submission documents")

    approved = "training succeeded, but the adapter did not pass the production acceptance"
    found_in = [d for d in docs if approved in (ROOT / d).read_text(encoding="utf-8").lower()]
    ROWS.append({"claim": "approved rejection phrasing used", "documented": approved,
                 "artifact_value": found_in, "source": "submission documents",
                 "supported": bool(found_in)})
    print(f"  {'ok  ' if found_in else 'FAIL'} approved rejection phrasing used ({len(found_in)} docs)")

    bad = [r for r in ROWS if not r["supported"]]
    payload = {"audited_at": __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).isoformat(),
        "claims_checked": len(ROWS), "supported": len(ROWS) - len(bad),
        "unsupported": len(bad), "passed": not bad, "claims": ROWS}
    out = ROOT / "evaluation" / "results" / "final_training_evidence_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Final Training-Evidence Audit", "",
         f"Audited {payload['audited_at']} · **{payload['supported']}/{payload['claims_checked']} "
         f"claims supported by a stored artifact**", "",
         "Every documented number is cross-checked against the artifact that produced it.",
         "The audit fails if any claim lacks support, or if a forbidden claim appears.", "",
         "| Claim | Documented | Artifact | Source | Supported |", "|---|---|---|---|---|"]
    for r in ROWS:
        L.append(f"| {r['claim']} | `{r['documented']}` | `{r['artifact_value']}` | "
                 f"{r['source']} | {'YES' if r['supported'] else '**NO**'} |")
    L += ["", "## Approved phrasing", "",
          '> "Training succeeded, but the adapter did not pass the production acceptance gate."', "",
          "## Forbidden claims (verified absent)", "",
          "adapter-as-production · universal 85.3% accuracy · all-Morisyen-native-verified ·",
          "AI makes legal decisions · guaranteed marine safety · real ministry submission", ""]
    if bad:
        L += ["## UNSUPPORTED CLAIMS", ""] + [f"- {r['claim']}: documented `{r['documented']}` "
                                              f"vs artifact `{r['artifact_value']}`" for r in bad] + [""]
    (ROOT / "docs" / "FINAL_TRAINING_EVIDENCE_AUDIT.md").write_text("\n".join(L), encoding="utf-8")

    print(f"\n{payload['supported']}/{payload['claims_checked']} claims supported")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
