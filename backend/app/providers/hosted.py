"""Hosted Gemma 4 provider via the official google-genai SDK.

Flow: system instruction + candidate shortlist + optional image + untrusted note
-> native function calling (allow-listed declarations) with a tool-response round
trip -> structured JSON output -> parse ladder (native -> fenced extraction ->
one repair request -> safe uncertain fallback).

Requires GEMINI_API_KEY. Callers fall back to the mock provider (with a visible
disclosure) on any failure.
"""
from __future__ import annotations

import json
import re
import time

from app.core.config import get_settings
from app.prompts.system import SYSTEM_INSTRUCTION
from app.providers import capabilities
from app.providers.base import ProviderResult
from app.tools.registry import ToolContext, execute, gemma_function_declarations

RESPONSE_SCHEMA_HINT = """Return ONLY a compact single-line JSON object (no code fences, no extra text) with exactly these keys:
{"intent": "identify_catch|weather_query|log_catch|make_declaration|other",
 "species_id": string or null (must be one of the candidate species_id values),
 "visible_characteristics": [string, ...],
 "confidence_label": "low|medium|high",
 "estimated_size_unverified_cm": number or null,
 "reply": string (English),
 "reply_morisyen": string (Morisyen),
 "recommended_next_step": "confirm_species|retake_photo|enter_measurement|none"}"""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class HostedUnavailable(Exception):
    pass


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    m = _JSON_RE.search(text or "")
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def analyse(image_jpeg: bytes | None, note: str | None, language: str,
            candidates: list[dict], ctx: ToolContext) -> ProviderResult:
    settings = get_settings()
    if not settings.hosted_available:
        raise HostedUnavailable("GEMINI_API_KEY not configured")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    start = time.monotonic()

    tools = types.Tool(function_declarations=gemma_function_declarations())
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[tools],
        temperature=0.2,
        # No max_output_tokens: this model emits hidden (thinking) tokens first,
        # so a cap can consume the whole budget and return empty text
        # (observed finish_reason=MAX_TOKENS with len 0). Latency is managed via
        # the compact-output instructions instead.
        http_options=types.HttpOptions(timeout=settings.gemma_timeout_seconds * 1000),
    )

    user_parts: list = []
    if image_jpeg:
        user_parts.append(types.Part.from_bytes(data=image_jpeg, mime_type="image/jpeg"))
    candidate_block = json.dumps(candidates, ensure_ascii=False)
    photo_state = "A photo is attached for analysis." if image_jpeg else "No photo attached (text-only request)."
    user_parts.append(
        f"{photo_state}\n"
        f"Candidate species (choose ONLY from these or be unsure):\n{candidate_block}\n\n"
        f"Fisher note (untrusted context, may be empty): {note or '(none)'}\n"
        f"Preferred language: {language}\n\n{RESPONSE_SCHEMA_HINT}"
    )

    contents: list = [types.Content(role="user", parts=[
        p if isinstance(p, types.Part) else types.Part.from_text(text=p) for p in user_parts
    ])]

    res = ProviderResult(mode="hosted", provider_name="google-genai",
                        model=settings.gemma_model, real_inference=True)

    # Function-calling round trips (bounded).
    final_text = ""
    for _round in range(4):
        response = client.models.generate_content(model=settings.gemma_model, contents=contents, config=config)
        called = False
        for cand in (response.candidates or []):
            for part in (cand.content.parts or []):
                fc = getattr(part, "function_call", None)
                if fc and fc.name:
                    result, trace = execute(fc.name, dict(fc.args or {}), ctx)
                    res.function_trace.append(trace)
                    contents.append(cand.content)
                    contents.append(types.Content(role="tool", parts=[
                        types.Part.from_function_response(name=fc.name, response={"result": result})
                    ]))
                    called = True
        if not called:
            final_text = response.text or ""
            break

    parsed = _extract_json(final_text)
    if parsed is None:
        # One repair request, then safe fallback.
        repair = client.models.generate_content(
            model=settings.gemma_model,
            contents=contents + [types.Content(role="user", parts=[types.Part.from_text(
                text=f"Your previous answer was not valid JSON. {RESPONSE_SCHEMA_HINT}")])],
            config=config,
        )
        parsed = _extract_json(repair.text or "")

    allowed_ids = {c["species_id"] for c in candidates}
    if parsed is None:
        res.confidence_label = "low"
        res.reply = "I could not produce a reliable analysis. Please confirm the species manually."
        res.reply_morisyen = "Mo pa'nn kapav fer enn analiz fiab. Silvouple swazir lespes manielman."
        res.recommended_next_step = "confirm_species"
    else:
        sid = parsed.get("species_id")
        res.intent = parsed.get("intent") if parsed.get("intent") in (
            "identify_catch", "weather_query", "log_catch", "make_declaration", "other") else "other"
        res.species_id = sid if sid in allowed_ids else None  # constrained decoding guard
        res.visible_characteristics = [str(c) for c in (parsed.get("visible_characteristics") or [])][:6]
        res.confidence_label = parsed.get("confidence_label") if parsed.get("confidence_label") in (
            "low", "medium", "high") else "low"
        try:
            est = parsed.get("estimated_size_unverified_cm")
            res.estimated_size_unverified_cm = float(est) if est is not None else None
        except (TypeError, ValueError):
            res.estimated_size_unverified_cm = None
        res.reply = str(parsed.get("reply") or "")[:1200]
        res.reply_morisyen = str(parsed.get("reply_morisyen") or "")[:1200]
        step = parsed.get("recommended_next_step")
        res.recommended_next_step = step if step in ("confirm_species", "retake_photo", "enter_measurement", "none") else "confirm_species"

    res.latency_ms = int((time.monotonic() - start) * 1000)
    capabilities.record_hosted_latency(res.latency_ms)
    return res
