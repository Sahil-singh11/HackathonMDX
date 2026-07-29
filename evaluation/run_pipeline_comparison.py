#!/usr/bin/env python3
"""Pipeline A routing measurement — hosted gemma-4-26b-a4b-it under the FROZEN compact prompt.

This establishes the product-level comparison point for AI Step 3:

    PIPELINE A  hosted 26B does routing AND image analysis
    PIPELINE B  fine-tuned E2B does compact routing; hosted 26B does image analysis

Only the routing half is measurable without a trained adapter, so that is what this
script measures — honestly labelled. Pipeline B's routing numbers come from the Kaggle
run and are merged in by `--merge-tuned`.

Uses the identical frozen compact prompt, the identical internal test split and the
identical scoring code as the notebook, so the numbers are comparable.

    cd backend && .venv/Scripts/python.exe ../evaluation/run_pipeline_comparison.py
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.prompts.compact_router_v1 import (ALLOWED_INTENTS, COMPACT_ROUTER_PROMPT,  # noqa: E402
                                           COMPACT_ROUTER_VERSION, ROUTABLE_TOOLS,
                                           compact_router_sha256)

DATA = ROOT / "training" / "data"
OUT = ROOT / "evaluation" / "results"

ROUTE_HINT = ('Return ONLY a JSON object: {"intent": one of '
              'identify_catch|weather_query|log_catch|make_declaration|other, '
              '"tool": an offered tool name or null, "arguments": object, '
              '"needs_more_information": true or false}')


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def parse_route(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def summarise(rows: list[dict], label: str) -> dict:
    def rate(key: str, subset=None) -> float | None:
        pool = [r for r in (subset if subset is not None else rows) if r.get(key) is not None]
        return round(sum(1 for r in pool if r[key]) / len(pool), 4) if pool else None

    safety = [r for r in rows if r["safety_category"] != "none"]
    mixed = [r for r in rows if "-" in r["language"]]
    english = [r for r in rows if r["group"] == "G"]
    uncertain = [r for r in rows if r["task"] == "uncertainty"]
    lat = [r["latency_ms"] for r in rows if r.get("latency_ms")]

    return {
        "label": label,
        "n": len(rows),
        "intent_accuracy": rate("intent_ok"),
        "tool_accuracy": rate("tool_ok"),
        "structured_validity": rate("structured_ok"),
        "valid_intent_enum_rate": rate("valid_intent_enum"),
        "tool_allow_list_rate": rate("tool_in_allow_list"),
        "unknown_function_rate": round(1 - (rate("tool_in_allow_list") or 1), 4),
        "safety_pass_rate": rate("tool_in_allow_list", safety),
        "mixed_language_accuracy": rate("intent_ok", mixed),
        "english_control_accuracy": rate("intent_ok", english),
        "uncertainty_accuracy": rate("intent_ok", uncertain),
        "api_failure_rate": round(sum(1 for r in rows if not r["api_ok"]) / len(rows), 4) if rows else 0.0,
        "median_latency_ms": int(statistics.median(lat)) if lat else None,
        "p90_latency_ms": int(sorted(lat)[min(len(lat) - 1, int(round(0.9 * (len(lat) - 1))))]) if lat else None,
        "hosted_calls": sum(1 for r in rows if r["api_ok"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge-tuned", type=Path, default=None,
                    help="Kaggle evaluation_metrics.json to merge as Pipeline B routing")
    args = ap.parse_args()

    settings = get_settings()
    if not settings.hosted_available:
        print("BLOCKED: GEMINI_API_KEY not configured")
        return 1

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    model = settings.gemma_model
    test_rows = load_jsonl(DATA / "test.jsonl")
    started = datetime.now(timezone.utc)

    cfg = types.GenerateContentConfig(
        system_instruction=COMPACT_ROUTER_PROMPT, temperature=0.2,
        http_options=types.HttpOptions(timeout=90_000))

    rows: list[dict] = []
    for rec in test_rows:
        user = (f"Tools available: {', '.join(rec['available_tools'])}\n\n"
                f"Fisher message: {rec['user_input']}\n\n{ROUTE_HINT}")
        t0 = time.monotonic()
        api_ok, text = True, ""
        try:
            r = client.models.generate_content(model=model, contents=user, config=cfg)
            text = r.text or ""
        except Exception as e:  # noqa: BLE001
            api_ok = False
            text = ""
            print(f"  {rec['id']}: API error {type(e).__name__}")
        ms = int((time.monotonic() - t0) * 1000)

        route = parse_route(text)
        pred_intent = (route or {}).get("intent")
        pred_tool = (route or {}).get("tool")
        row = {
            "id": rec["id"], "group": rec["group"], "task": rec["task"],
            "language": rec["language"], "safety_category": rec["safety_category"],
            "expected_intent": rec["expected_intent"], "pred_intent": pred_intent,
            "intent_ok": pred_intent == rec["expected_intent"],
            "expected_tool": rec["expected_tool_call"], "pred_tool": pred_tool,
            "tool_ok": pred_tool == rec["expected_tool_call"],
            "structured_ok": route is not None,
            "valid_intent_enum": pred_intent in ALLOWED_INTENTS,
            "tool_in_allow_list": pred_tool is None or pred_tool in ROUTABLE_TOOLS,
            "api_ok": api_ok, "latency_ms": ms,
        }
        rows.append(row)
        print(f"  [{'ok ' if row['intent_ok'] else 'BAD'}] {rec['id']:<28} "
              f"exp={rec['expected_intent']:<16} got={str(pred_intent):<16} {ms}ms", flush=True)

    pipeline_a = summarise(rows, "pipeline_a_hosted_26b_compact_routing")

    payload = {
        "run_at": started.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "compact_prompt_version": COMPACT_ROUTER_VERSION,
        "compact_prompt_sha256": compact_router_sha256(),
        "test_split": "training/data/test.jsonl",
        "test_records": len(test_rows),
        "pipeline_a": {
            "description": "Hosted gemma-4-26b-a4b-it performs routing AND image analysis.",
            "routing_model": model,
            "image_model": model,
            "hosted_calls_per_routing_request": 1,
            "routing": pipeline_a,
        },
        "pipeline_b": {
            "description": ("Fine-tuned gemma-4-E2B-it router performs compact intent/tool "
                            "routing; hosted gemma-4-26b-a4b-it keeps image analysis."),
            "routing_model": "google/gemma-4-E2B-it + LoRA adapter",
            "image_model": model,
            "hosted_calls_per_routing_request": 0,
            "routing": None,
            "status": "not measured — no accepted adapter",
        },
        "verdict": ("Pipeline B is NOT claimed better. Its routing half is unmeasured until a "
                    "tuned adapter passes the Step-3 acceptance gate."),
    }

    if args.merge_tuned and args.merge_tuned.exists():
        tuned = json.loads(args.merge_tuned.read_text(encoding="utf-8"))
        t = tuned.get("tuned_internal")
        if t:
            payload["pipeline_b"]["routing"] = t
            payload["pipeline_b"]["status"] = "measured on Kaggle"
            a_acc = pipeline_a["intent_accuracy"] or 0
            b_acc = t.get("intent_accuracy") or 0
            payload["verdict"] = (
                f"Pipeline B routing intent accuracy {b_acc:.3f} vs Pipeline A {a_acc:.3f}. "
                + ("Pipeline B is better on routing accuracy AND removes a hosted call."
                   if b_acc > a_acc else
                   "Pipeline B is NOT better on routing accuracy; Pipeline A remains production."))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "system_pipeline_comparison.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + json.dumps(pipeline_a, indent=2))
    print(f"\nWrote evaluation/results/system_pipeline_comparison.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
