"""Hosted Gemma 4 provider via the official google-genai SDK.

Two-turn lifecycle (validated in Step 1, kept in Step 2):

    TURN 1  user request + allow-listed tool declarations -> the model may pick a function
    APP     validate name, validate arguments, execute, redact
    TURN 2  tool result returned -> final user-facing STRUCTURED response

Turn 1 must stay unstructured: a response schema and a `function_call` part compete
for the same output, so tool selection is asked for on its own.

Turn 2 uses PROMPT-INSTRUCTED JSON, not a native response schema. That is the Step-2
measured result, not a default: across 88 requests, `response_json_schema` reached only
72.7% final validity and 59.1% exact enum validity with a p90 of 53.5 s (the model
intermittently writes until the output ceiling), while the prompt-instructed control
reached 100% / 100% with a p90 of 8.25 s. See docs/AI_PRODUCTION_CONFIG_DECISION.md.
The native path stays selectable in `app.providers.structured` for re-testing.

Parse ladder: native schema -> transport model -> deterministic conversion; on failure,
`coerce_to_schema()` at the boundary; then one repair request; then a safe uncertain
response. Callers fall back to the mock (with a visible disclosure) on any exception.

Requires GEMINI_API_KEY.
"""
from __future__ import annotations

import json
import time

from app.core.config import get_settings
from app.prompts.system import SYSTEM_INSTRUCTION
from app.providers import capabilities, profiles, structured
from app.providers.base import ProviderResult
from app.providers.structured import MODE_JSON_SCHEMA, MODE_PROMPT_FALLBACK, call_structured
from app.tools.registry import ToolContext, execute, gemma_function_declarations

MAX_TOOL_ROUNDS = 3

# The structured-output mechanism selected by the Step-2 experiments. Named explicitly so
# the active mode is always visible in diagnostics and never switches silently.
PRODUCTION_MODE = MODE_PROMPT_FALLBACK

RESPONSE_SCHEMA_HINT = """Return ONLY a compact single-line JSON object (no code fences, no extra text) with exactly these keys:
{"intent": "identify_catch|weather_query|log_catch|make_declaration|other",
 "species_suggestion": {"species_id": string or null, "morisyen": string or null,
                        "english": string or null, "scientific": string or null},
 "visible_characteristics": [string, ...], "confidence_label": "low|medium|high",
 "species_confirmation_required": true, "estimated_size_unverified_cm": number or null,
 "measured_size_required": true, "reply": string (English), "reply_morisyen": string (Morisyen),
 "recommended_next_step": "confirm_species|retake_photo|enter_measurement|none",
 "requested_function": string or null, "limitations": [string, ...]}
species_suggestion.species_id MUST be one of the supplied candidate species_id values, or null."""


class HostedUnavailable(Exception):
    pass


def _user_content(types, image_jpeg: bytes | None, note: str | None, language: str,
                  candidates: list[dict], extra: str = ""):
    """Candidate shortlist only — never the whole catalogue."""
    candidate_block = json.dumps(candidates, ensure_ascii=False)
    photo_state = "A photo is attached." if image_jpeg else "No photo attached (text-only request)."
    text = (f"{photo_state}\n"
            f"Candidate species (choose ONLY from these, or null):\n{candidate_block}\n\n"
            f"Fisher note (untrusted context, may be empty): {note or '(none)'}\n"
            f"Preferred language: {language}")
    if extra:
        text = f"{text}\n\n{extra}"
    parts = []
    if image_jpeg:
        parts.append(types.Part.from_bytes(data=image_jpeg, mime_type="image/jpeg"))
    parts.append(types.Part.from_text(text=text))
    return types.Content(role="user", parts=parts)


def analyse(image_jpeg: bytes | None, note: str | None, language: str,
            candidates: list[dict], ctx: ToolContext) -> ProviderResult:
    settings = get_settings()
    if not settings.hosted_available:
        raise HostedUnavailable("GEMINI_API_KEY not configured")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    model = settings.gemma_model
    start = time.monotonic()
    allowed_ids = {c["species_id"] for c in candidates}

    res = ProviderResult(mode="hosted", provider_name="google-genai",
                         model=model, real_inference=True)
    stages: dict[str, int] = {}

    # ---------------------------------------------------------------- TURN 1
    sel = profiles.FAST_TOOL_SELECTION
    tool_cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[types.Tool(function_declarations=gemma_function_declarations())],
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_level=sel.thinking_level),
        http_options=types.HttpOptions(timeout=sel.timeout_seconds * 1000),
    )

    contents: list = [_user_content(types, image_jpeg, note, language, candidates)]

    # Turn 1 deliberately gets a LEAN prompt: choosing an allow-listed function needs the
    # note, not the photo or the candidate block. Sending the full context here measured
    # 10-19 s; the note alone measures ~1.4 s. The full context is restored for turn 2.
    selection_contents: list = [types.Content(role="user", parts=[types.Part.from_text(
        text=(f"Fisher note (untrusted context, may be empty): {note or '(none)'}\n"
              f"Preferred language: {language}\n"
              f"{'A photo is attached to this request.' if image_jpeg else 'No photo attached.'}\n"
              "If a function would help answer this, request it. Otherwise answer normally."))])]

    tool_history: list = []
    t0 = time.monotonic()
    for _round in range(MAX_TOOL_ROUNDS):
        response = client.models.generate_content(model=model,
                                                  contents=selection_contents + tool_history,
                                                  config=tool_cfg)
        calls = [p.function_call for cand in (response.candidates or [])
                 for p in (getattr(cand.content, "parts", None) or [])
                 if getattr(p, "function_call", None) and p.function_call.name]
        if not calls:
            break
        tool_history.append(response.candidates[0].content)
        for fc in calls:
            tt = time.monotonic()
            # Name and arguments are validated inside execute(); an unknown name or a
            # bad argument set is rejected there and never reaches a handler.
            result, trace = execute(fc.name, dict(fc.args or {}), ctx)
            stages["tool_execution_ms"] = stages.get("tool_execution_ms", 0) + int((time.monotonic() - tt) * 1000)
            res.function_trace.append(trace)
            tool_history.append(types.Content(role="tool", parts=[
                types.Part.from_function_response(name=fc.name, response={"result": result})]))
    stages["turn1_tool_selection_ms"] = int((time.monotonic() - t0) * 1000)

    # ---------------------------------------------------------------- TURN 2
    prof = profiles.for_request(has_image=image_jpeg is not None,
                                stage="final_tool_response" if tool_history else "analysis")
    final_cfg = structured.build_config(
        types, PRODUCTION_MODE, system_instruction=SYSTEM_INSTRUCTION, tools=None,
        thinking_level=prof.thinking_level, max_output_tokens=prof.max_output_tokens,
        timeout_ms=prof.timeout_seconds * 1000)

    final_contents = contents + tool_history
    closing = RESPONSE_SCHEMA_HINT if PRODUCTION_MODE == MODE_PROMPT_FALLBACK else ""
    if tool_history:
        closing = ("Now give the fisher the final answer using the tool result above.\n\n"
                   + closing).strip()
    if closing:
        final_contents = final_contents + [types.Content(
            role="user", parts=[types.Part.from_text(text=closing)])]

    diag, app_model, _raw = call_structured(client, model, final_contents, final_cfg,
                                            PRODUCTION_MODE, allowed_ids)
    stages["turn2_structured_ms"] = diag.latency_ms

    # One controlled repair, then the safe uncertain response.
    if app_model is None:
        diag.repair_applied = True
        t0 = time.monotonic()
        repair_contents = final_contents + [types.Content(role="user", parts=[types.Part.from_text(
            text=f"Your previous answer could not be used. {RESPONSE_SCHEMA_HINT}")])]
        diag2, app_model, _raw2 = call_structured(client, model, repair_contents, final_cfg,
                                                  PRODUCTION_MODE, allowed_ids)
        stages["repair_ms"] = int((time.monotonic() - t0) * 1000)
        diag.final_schema_valid = diag2.final_schema_valid
        diag.coercion_applied = diag.coercion_applied or diag2.coercion_applied
        diag.coercion_fields = sorted(set(diag.coercion_fields) | set(diag2.coercion_fields))
        if diag2.fallback_reason:
            diag.fallback_reason = diag2.fallback_reason

    if app_model is None:
        res.confidence_label = "low"
        res.reply = "I could not produce a reliable analysis. Please confirm the species manually."
        res.reply_morisyen = "Mo pa'nn kapav fer enn analiz fiab. Silvouple swazir lespes manielman."
        res.recommended_next_step = "confirm_species"
        diag.fallback_reason = diag.fallback_reason or "safe_uncertain_response"
    else:
        res.intent = app_model.intent
        res.species_id = app_model.species_suggestion.species_id
        res.visible_characteristics = app_model.visible_characteristics[:6]
        res.confidence_label = app_model.confidence_label
        res.estimated_size_unverified_cm = app_model.estimated_size_unverified_cm
        res.reply = app_model.reply
        res.reply_morisyen = app_model.reply_morisyen
        res.recommended_next_step = app_model.recommended_next_step

    res.latency_ms = int((time.monotonic() - start) * 1000)
    stages["total_ms"] = res.latency_ms
    capabilities.record_hosted_latency(res.latency_ms)

    # Internal only — never merged into AnalyseCatchResponse.
    res.diagnostics = {
        "structured_mode": diag.mode,
        "profile": prof.name,
        "tool_selection_profile": sel.name,
        "native_schema_valid": diag.native_schema_valid,
        "exact_enum_valid": diag.exact_enum_valid,
        "parsed_object_returned": diag.parsed_object_returned,
        "coercion_applied": diag.coercion_applied,
        "coercion_fields": diag.coercion_fields,
        "repair_applied": diag.repair_applied,
        "fallback_reason": diag.fallback_reason,
        "final_schema_valid": diag.final_schema_valid,
        "finish_reason": diag.finish_reason,
        "prompt_tokens": diag.prompt_tokens,
        "output_tokens": diag.output_tokens,
        "thought_tokens": diag.thought_tokens,
        "stages_ms": stages,
    }
    return res


# Kept so the Step-1 control path stays runnable and comparable.
CONTROL_MODE = MODE_PROMPT_FALLBACK
