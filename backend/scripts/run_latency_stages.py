#!/usr/bin/env python3
"""AI Step 2 — staged latency benchmark.

Step 1 recorded one number for a whole tool round trip, which hides where the
time goes. This measures each stage separately:

    image preprocessing · first model request · tool execution ·
    second model request · validation/repair · total end-to-end

and reports text-only, image, function-selection, tool round trip and final
structured response independently. Also compares thinking levels and image
longest-side values on identical inputs.

    cd backend && .venv/Scripts/python.exe scripts/run_latency_stages.py

Writes evaluation/results/latency_stages.json. Synthetic/redistributable inputs
only; no prompt text or model prose is stored.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
ROOT = BACKEND.parent

from app.core.config import get_settings  # noqa: E402
from app.prompts.system import COMPACT_SYSTEM_INSTRUCTION  # noqa: E402
from app.providers import structured  # noqa: E402
from app.providers.profiles import MIN_SAFE_OUTPUT_CAP, THINKING_HIGH, THINKING_MINIMAL  # noqa: E402
from app.providers.structured import MODE_JSON_SCHEMA  # noqa: E402
from app.services.species.retrieval import candidates_for, public_candidate  # noqa: E402
from app.tools.registry import ToolContext, execute, gemma_function_declarations  # noqa: E402

MARINE_Q = "Ki kondisyon lamer pou dime dan Flic-en-Flac?"
TEXT_Q = "Mo finn gagn enn pwason. Ed mwa anrezistre li."
REPEATS = 3


def stats(vals: list[int]) -> dict:
    if not vals:
        return {}
    s = sorted(vals)
    p90 = s[min(len(s) - 1, int(round(0.9 * (len(s) - 1))))]
    return {"n": len(s), "min_ms": s[0], "max_ms": s[-1], "avg_ms": int(statistics.mean(s)),
            "median_ms": int(statistics.median(s)), "p90_ms": int(p90)}


def preprocess(path: Path, longest: int) -> tuple[bytes, int]:
    t0 = time.monotonic()
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((longest, longest))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), int((time.monotonic() - t0) * 1000)


def main() -> int:
    s = get_settings()
    if not s.hosted_available:
        print("BLOCKED: GEMINI_API_KEY not configured")
        return 1

    from google import genai
    from google.genai import types
    from sqlmodel import Session

    from app.db.session import get_engine, init_db

    client = genai.Client(api_key=s.gemini_api_key)
    model = s.gemma_model
    candidates = [public_candidate(c) for c in candidates_for(None)]
    allowed = {c["species_id"] for c in candidates}
    cblock = json.dumps(candidates, ensure_ascii=False)
    hero = sorted((ROOT / "data" / "demo").glob("epinephelus_merra_*.jpg"))[0]
    init_db()

    out: dict = {"run_at": datetime.now(timezone.utc).isoformat(), "model": model,
                 "repeats": REPEATS, "stages": {}, "thinking_comparison": {},
                 "image_size_comparison": {}}

    def structured_cfg(thinking=THINKING_MINIMAL, cap=MIN_SAFE_OUTPUT_CAP, tools=None, timeout=90_000):
        return structured.build_config(
            types, MODE_JSON_SCHEMA if tools is None else structured.MODE_PROMPT_FALLBACK,
            system_instruction=COMPACT_SYSTEM_INSTRUCTION, tools=tools,
            thinking_level=thinking, max_output_tokens=cap if tools is None else None,
            timeout_ms=timeout)

    def user(text: str, img: bytes | None = None):
        parts = []
        if img:
            parts.append(types.Part.from_bytes(data=img, mime_type="image/jpeg"))
        parts.append(types.Part.from_text(text=text))
        return [types.Content(role="user", parts=parts)]

    # ---------------- stage: text-only structured request
    lat = []
    for _ in range(REPEATS):
        diag, _m, _r = structured.call_structured(
            client, model, user(f"Candidates:\n{cblock}\n\nFisher note (untrusted): {TEXT_Q}\nNo photo."),
            structured_cfg(), MODE_JSON_SCHEMA, allowed)
        if diag.api_ok:
            lat.append(diag.latency_ms)
        print(f"  text_only {diag.latency_ms}ms native={diag.native_schema_valid}", flush=True)
    out["stages"]["text_only_structured"] = stats(lat)

    # ---------------- stage: image request (incl. preprocessing, reported separately)
    lat, pre = [], []
    for _ in range(REPEATS):
        img, pms = preprocess(hero, 1024)
        pre.append(pms)
        diag, _m, _r = structured.call_structured(
            client, model, user(f"Candidates:\n{cblock}\n\nFisher note (untrusted): Ki pwason sa?\nA photo is attached.", img),
            structured_cfg(), MODE_JSON_SCHEMA, allowed)
        if diag.api_ok:
            lat.append(diag.latency_ms)
        print(f"  image {diag.latency_ms}ms (preprocess {pms}ms) native={diag.native_schema_valid}", flush=True)
    out["stages"]["image_preprocessing"] = stats(pre)
    out["stages"]["image_structured"] = stats(lat)

    # ---------------- stage: function selection (turn 1), tool exec, final response (turn 2)
    tools = types.Tool(function_declarations=gemma_function_declarations())
    fc_cfg = types.GenerateContentConfig(
        system_instruction=COMPACT_SYSTEM_INSTRUCTION, tools=[tools], temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_MINIMAL),
        http_options=types.HttpOptions(timeout=90_000))
    t1s, tools_ms, t2s, totals = [], [], [], []
    for _ in range(REPEATS):
        total0 = time.monotonic()
        t0 = time.monotonic()
        try:
            r = client.models.generate_content(model=model, contents=MARINE_Q, config=fc_cfg)
        except Exception as e:  # noqa: BLE001
            print(f"  turn1 FAILED {type(e).__name__}", flush=True)
            continue
        t1 = int((time.monotonic() - t0) * 1000)
        t1s.append(t1)

        fc = None
        for cand in (r.candidates or []):
            for p in (getattr(cand.content, "parts", None) or []):
                if getattr(p, "function_call", None) and p.function_call.name:
                    fc = p.function_call
        if fc is None:
            print(f"  turn1 {t1}ms — no function requested", flush=True)
            continue

        t0 = time.monotonic()
        with Session(get_engine()) as sess:
            ctx = ToolContext(session=sess, language="mfe", allow_network=True)
            result, trace = execute(fc.name, dict(fc.args or {}), ctx)
        tms = int((time.monotonic() - t0) * 1000)
        tools_ms.append(tms)

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=MARINE_Q)]),
            r.candidates[0].content,
            types.Content(role="tool", parts=[types.Part.from_function_response(
                name=fc.name, response={"result": result})]),
            types.Content(role="user", parts=[types.Part.from_text(
                text="Now give the fisher the final answer. Do not say conditions are safe.")]),
        ]
        diag, _m, _r = structured.call_structured(
            client, model, contents, structured_cfg(), MODE_JSON_SCHEMA, allowed)
        t2s.append(diag.latency_ms)
        totals.append(int((time.monotonic() - total0) * 1000))
        print(f"  turn1={t1}ms tool={tms}ms turn2={diag.latency_ms}ms total={totals[-1]}ms "
              f"fn={fc.name} native={diag.native_schema_valid}", flush=True)

    out["stages"]["function_selection_turn1"] = stats(t1s)
    out["stages"]["tool_execution"] = stats(tools_ms)
    out["stages"]["final_structured_turn2"] = stats(t2s)
    out["stages"]["tool_round_trip_total"] = stats(totals)

    # ---------------- thinking comparison on identical inputs
    for level in (THINKING_MINIMAL, THINKING_HIGH):
        lat, native = [], 0
        for _ in range(REPEATS):
            img, _ = preprocess(hero, 1024)
            diag, _m, _r = structured.call_structured(
                client, model, user(f"Candidates:\n{cblock}\n\nFisher note (untrusted): Ki pwason sa?\nA photo is attached.", img),
                structured_cfg(thinking=level), MODE_JSON_SCHEMA, allowed)
            if diag.api_ok:
                lat.append(diag.latency_ms)
                native += 1 if diag.native_schema_valid else 0
        out["thinking_comparison"][level] = {**stats(lat), "native_valid": native, "of": REPEATS}
        print(f"  thinking {level}: {out['thinking_comparison'][level]}", flush=True)

    # ---------------- image size comparison on identical image
    for longest in (768, 1024, 1280):
        lat, native, sizes = [], 0, []
        for _ in range(REPEATS):
            img, pms = preprocess(hero, longest)
            sizes.append(len(img))
            diag, _m, _r = structured.call_structured(
                client, model, user(f"Candidates:\n{cblock}\n\nFisher note (untrusted): Ki pwason sa?\nA photo is attached.", img),
                structured_cfg(), MODE_JSON_SCHEMA, allowed)
            if diag.api_ok:
                lat.append(diag.latency_ms)
                native += 1 if diag.native_schema_valid else 0
        out["image_size_comparison"][str(longest)] = {
            **stats(lat), "native_valid": native, "of": REPEATS,
            "avg_jpeg_bytes": int(statistics.mean(sizes))}
        print(f"  image {longest}px: {out['image_size_comparison'][str(longest)]}", flush=True)

    dest = ROOT / "evaluation" / "results" / "latency_stages.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
