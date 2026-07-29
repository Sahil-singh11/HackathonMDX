#!/usr/bin/env python3
"""One-off SDK/model capability probe for AI Step 2.

Answers, against the REAL model, which structured-output mechanisms
google-genai actually supports for gemma-4-26b-a4b-it. Writes a JSON result so
the experiment plan is based on measurement, not assumption.

    cd backend && .venv/Scripts/python.exe scripts/probe_structured_support.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
ROOT = BACKEND.parent

from app.core.config import get_settings  # noqa: E402
from app.schemas.transport import GemmaTransportAnalysis  # noqa: E402

PROMPT = "A fisher says: I caught a fish near the reef. Respond helpfully in one short sentence."
OUT = ROOT / "evaluation" / "results" / "sdk_capability_probe.json"


def main() -> int:
    s = get_settings()
    if not s.hosted_available:
        print("BLOCKED: no GEMINI_API_KEY")
        return 1

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=s.gemini_api_key)
    model = s.gemma_model
    results: list[dict] = []

    PROBE_TIMEOUT_MS = 90_000  # a config that cannot answer a one-line prompt in 90s is unusable

    def probe(name: str, cfg, prompt: str = PROMPT) -> dict:
        # Bound every probe: one config makes this model emit until the output
        # ceiling (observed 32768 tokens / ~12 min), which must be recorded as a
        # failure mode rather than allowed to hang the run.
        cfg.http_options = types.HttpOptions(timeout=PROBE_TIMEOUT_MS)
        t0 = time.monotonic()
        row: dict = {"probe": name}
        try:
            r = client.models.generate_content(model=model, contents=prompt, config=cfg)
            ms = int((time.monotonic() - t0) * 1000)
            um = r.usage_metadata
            text = r.text or ""
            row.update({
                "supported": True, "latency_ms": ms,
                "parsed_type": type(r.parsed).__name__,
                "parsed_is_model": isinstance(r.parsed, GemmaTransportAnalysis),
                "text_is_json": _is_json(text),
                "text_head": " ".join(text.split())[:160],
                "prompt_tokens": um.prompt_token_count,
                "output_tokens": um.candidates_token_count,
                "thought_tokens": um.thoughts_token_count,
                "finish_reason": str(getattr((r.candidates or [None])[0], "finish_reason", None)),
            })
        except Exception as e:  # noqa: BLE001 — an unsupported config is a result
            row.update({"supported": False, "latency_ms": int((time.monotonic() - t0) * 1000),
                        "error_type": type(e).__name__, "error": str(e)[:300]})
        results.append(row)
        print(json.dumps(row, ensure_ascii=False)[:400], flush=True)
        return row

    def _is_json(text: str) -> bool:
        try:
            json.loads(text)
            return True
        except Exception:  # noqa: BLE001
            return False

    # --- structured-output mechanisms
    probe("baseline_no_config", types.GenerateContentConfig(temperature=0.2))
    probe("response_mime_type_only",
          types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json"))
    probe("mime_plus_pydantic_response_schema",
          types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json",
                                      response_schema=GemmaTransportAnalysis))
    probe("mime_plus_response_json_schema",
          types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json",
                                      response_json_schema=GemmaTransportAnalysis.model_json_schema()))

    # --- thinking levels
    for level in ("MINIMAL", "HIGH"):
        probe(f"thinking_{level.lower()}",
              types.GenerateContentConfig(temperature=0.2,
                                          thinking_config=types.ThinkingConfig(thinking_level=level)))
    probe("thinking_budget_0",
          types.GenerateContentConfig(temperature=0.2,
                                      thinking_config=types.ThinkingConfig(thinking_budget=0)))

    # --- output cap interaction with hidden thinking tokens
    for cap in (256, 384, 1024):
        probe(f"max_output_tokens_{cap}",
              types.GenerateContentConfig(temperature=0.2, max_output_tokens=cap))

    # --- structured output combined with function declarations (must not conflict)
    from app.tools.registry import gemma_function_declarations
    tools = types.Tool(function_declarations=gemma_function_declarations())
    probe("tools_plus_response_schema",
          types.GenerateContentConfig(temperature=0.2, tools=[tools],
                                      response_mime_type="application/json",
                                      response_schema=GemmaTransportAnalysis),
          prompt="Ki kondisyon lamer pou dime dan Flic-en-Flac?")
    probe("tools_only",
          types.GenerateContentConfig(temperature=0.2, tools=[tools]),
          prompt="Ki kondisyon lamer pou dime dan Flic-en-Flac?")

    # --- Interactions API availability (inspection only, no migration)
    interactions: dict = {"client_has_interactions": hasattr(client, "interactions")}
    try:
        import inspect
        from google.genai import interactions as _int_mod  # noqa: F401
        interactions["module_importable"] = True
        interactions["methods"] = [m for m in dir(client.interactions) if not m.startswith("_")]
        sig = inspect.signature(client.interactions.create) if hasattr(client.interactions, "create") else None
        interactions["create_params"] = list(sig.parameters) if sig else None
    except Exception as e:  # noqa: BLE001
        interactions["module_importable"] = False
        interactions["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    print(json.dumps(interactions)[:400], flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"model": model, "sdk": "google-genai",
                               "interactions_api": interactions,
                               "probes": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
