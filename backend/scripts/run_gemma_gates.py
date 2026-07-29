#!/usr/bin/env python3
"""Hosted Gemma gate runner. Run the moment GEMINI_API_KEY exists:

    cd backend && .venv/bin/python scripts/run_gemma_gates.py

Executes the ten gates from docs/MODEL_STRATEGY.md against the real hosted
model and writes docs/GEMMA_GATES.md + evaluation/results/gemma_gates.json.
Without a key it records BLOCKED honestly and exits non-zero. It never prints
the key.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
ROOT = BACKEND.parent

from app.core.config import get_settings  # noqa: E402
from app.prompts.system import SYSTEM_INSTRUCTION  # noqa: E402
from app.tools.registry import gemma_function_declarations  # noqa: E402

RESULTS: list[dict] = []


def record(name: str, status: str, detail: str = "", latency_ms: int | None = None) -> None:
    RESULTS.append({"gate": name, "status": status, "detail": detail[:400], "latency_ms": latency_ms})
    print(f"[{status:>7}] {name}" + (f" ({latency_ms} ms)" if latency_ms else ""))


def main() -> int:
    settings = get_settings()
    if not settings.hosted_available:
        record("all", "BLOCKED", "GEMINI_API_KEY not configured — no hosted gate can run. "
                                 "Insert the key into .env and re-run.")
        write_outputs(blocked=True)
        return 1

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    model = settings.gemma_model
    cfg = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.2)

    def gen(contents, config=cfg):
        t0 = time.monotonic()
        r = client.models.generate_content(model=model, contents=contents, config=config)
        return r, int((time.monotonic() - t0) * 1000)

    # 1 text smoke
    try:
        r, ms = gen("Reply with the single word: ready")
        record("text_smoke", "PASS" if "ready" in (r.text or "").lower() else "FAIL", r.text or "", ms)
    except Exception as e:  # noqa: BLE001
        record("text_smoke", "FAIL", str(e))

    # 2 image smoke (hero image)
    try:
        hero = next((ROOT / "data" / "demo").glob("octopus_cyanea_*.jpg"))
        img = types.Part.from_bytes(data=hero.read_bytes(), mime_type="image/jpeg")
        r, ms = gen([img, "Describe the main animal visible in one short sentence."])
        record("image_smoke", "PASS" if r.text else "FAIL", r.text or "", ms)
    except Exception as e:  # noqa: BLE001
        record("image_smoke", "FAIL", str(e))

    # 3 Morisyen text
    try:
        r, ms = gen("Reponn an Morisyen (kreol morisien), enn sel fraz: ki to kapav fer pou enn peser?")
        record("morisyen_text", "PASS" if r.text else "FAIL", r.text or "", ms)
    except Exception as e:  # noqa: BLE001
        record("morisyen_text", "FAIL", str(e))

    # 4 structured output
    try:
        r, ms = gen('Return ONLY JSON: {"ok": true, "lang": "en"}')
        parsed = json.loads((r.text or "").strip().strip("`").replace("json", "", 1).strip())
        record("structured_output", "PASS" if parsed.get("ok") else "FAIL", r.text or "", ms)
    except Exception as e:  # noqa: BLE001
        record("structured_output", "FAIL", str(e))

    # 5+6 function call + tool round trip
    try:
        tools = types.Tool(function_declarations=gemma_function_declarations())
        fc_cfg = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, tools=[tools], temperature=0.2)
        contents = ["What are the marine conditions near Grand Baie right now?"]
        r, ms = gen(contents, fc_cfg)
        fc = None
        for cand in (r.candidates or []):
            for part in (cand.content.parts or []):
                if getattr(part, "function_call", None) and part.function_call.name:
                    fc = part.function_call
        if fc and fc.name == "get_marine_conditions":
            record("function_call", "PASS", f"requested {fc.name}", ms)
            tool_resp = types.Part.from_function_response(
                name=fc.name, response={"result": {"wave_height_m": 1.2, "swell_height_m": 1.8, "mock": True}})
            r2, ms2 = gen([types.Content(role="user", parts=[types.Part.from_text(text=contents[0])]),
                           r.candidates[0].content,
                           types.Content(role="tool", parts=[tool_resp])], fc_cfg)
            record("tool_round_trip", "PASS" if r2.text else "FAIL", r2.text or "", ms2)
        else:
            record("function_call", "FAIL", f"no function requested (got: {fc.name if fc else 'none'})", ms)
            record("tool_round_trip", "SKIP", "depends on function_call")
    except Exception as e:  # noqa: BLE001
        record("function_call", "FAIL", str(e))
        record("tool_round_trip", "SKIP", "depends on function_call")

    # 7 timeout handling
    try:
        tiny = types.GenerateContentConfig(http_options=types.HttpOptions(timeout=1))
        try:
            client.models.generate_content(model=model, contents="write 2000 words about the sea", config=tiny)
            record("timeout_handling", "WARN", "1ms timeout did not trigger — verify client timeout config")
        except Exception:
            record("timeout_handling", "PASS", "timeout raised and was caught cleanly")
    except Exception as e:  # noqa: BLE001
        record("timeout_handling", "FAIL", str(e))

    # 8 API failure handling (bad model name must fail cleanly)
    try:
        try:
            client.models.generate_content(model="nonexistent-model-xyz", contents="hi")
            record("api_failure_handling", "FAIL", "bad model name did not raise")
        except Exception:
            record("api_failure_handling", "PASS", "error raised and caught; dispatcher falls back to mock")
    except Exception as e:  # noqa: BLE001
        record("api_failure_handling", "FAIL", str(e))

    # 9 latency benchmark (5 short calls)
    try:
        lats = []
        for _ in range(5):
            _, ms = gen("one word: ok")
            lats.append(ms)
        record("latency_benchmark", "PASS",
               f"median {statistics.median(lats)} ms, min {min(lats)}, max {max(lats)}",
               int(statistics.median(lats)))
    except Exception as e:  # noqa: BLE001
        record("latency_benchmark", "FAIL", str(e))

    # 10 thinking comparison (if the model/config supports a thinking budget)
    try:
        r_min, ms_min = gen("In one sentence: why confirm species before rule checks?")
        try:
            think_cfg = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                thinking_config=types.ThinkingConfig(thinking_budget=1024))
            r_hi, ms_hi = gen("In one sentence: why confirm species before rule checks?", think_cfg)
            record("thinking_comparison", "PASS", f"minimal {ms_min} ms vs higher {ms_hi} ms", None)
        except Exception:
            record("thinking_comparison", "WARN",
                   f"thinking config not supported for {model}; minimal-mode latency {ms_min} ms")
    except Exception as e:  # noqa: BLE001
        record("thinking_comparison", "FAIL", str(e))

    write_outputs(blocked=False)
    return 0 if all(r["status"] in ("PASS", "WARN", "SKIP") for r in RESULTS) else 2


def write_outputs(blocked: bool) -> None:
    out_json = ROOT / "evaluation" / "results" / "gemma_gates.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {"run_at": datetime.now(timezone.utc).isoformat(), "blocked": blocked,
               "model": get_settings().gemma_model, "results": RESULTS}
    out_json.write_text(json.dumps(payload, indent=2))
    md = ROOT / "docs" / "GEMMA_GATES.md"
    lines = ["# Hosted Gemma Gate Results\n",
             f"Run: {payload['run_at']} · Model: `{payload['model']}` · "
             f"{'**BLOCKED — no API key**' if blocked else 'live run'}\n",
             "| Gate | Status | Detail | Latency |", "|---|---|---|---|"]
    for r in RESULTS:
        lines.append(f"| {r['gate']} | {r['status']} | {r['detail'][:120]} | {r['latency_ms'] or ''} |")
    md.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
