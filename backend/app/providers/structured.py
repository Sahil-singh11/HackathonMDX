"""Structured-output adapter: explicit mode selection, never silent.

Modes, strongest first:

    generate_content_pydantic_schema  response_mime_type + response_schema=<Pydantic>
    generate_content_json_schema      response_mime_type + response_json_schema=<dict>
    interactions_response_format      Interactions API response_format (only if real)
    prompt_json_fallback              Step-1 control: JSON asked for in the prompt

Selection is explicit: a caller names the mode, or `best_supported_mode()` picks
one from a probed capability map. Nothing here silently downgrades — a mode that
fails raises, and the caller records the failure and decides.

The active mode is recorded in provider diagnostics (internal), not in the public
API response.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from app.schemas.transport import GemmaTransportAnalysis

MODE_PYDANTIC = "generate_content_pydantic_schema"
MODE_JSON_SCHEMA = "generate_content_json_schema"
MODE_INTERACTIONS = "interactions_response_format"
MODE_PROMPT_FALLBACK = "prompt_json_fallback"

ALL_MODES = (MODE_PYDANTIC, MODE_JSON_SCHEMA, MODE_INTERACTIONS, MODE_PROMPT_FALLBACK)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class StructuredCall:
    """Everything measured about one structured-output attempt.

    Deliberately carries no prompt text, no image bytes and no chain of thought —
    only shapes, flags, counts and timings, so it is safe to serialise into
    evaluation artifacts.
    """

    mode: str
    latency_ms: int = 0
    api_ok: bool = False
    error_type: str | None = None

    raw_json_parsed: bool = False          # response body was parseable JSON
    parsed_object_returned: bool = False   # SDK response.parsed gave a model instance
    native_schema_valid: bool = False      # raw output validated against the transport schema untouched
    exact_enum_valid: bool = False         # every enum field was already a legal value

    coercion_applied: bool = False
    coercion_fields: list[str] = field(default_factory=list)
    repair_applied: bool = False
    fallback_reason: str | None = None
    final_schema_valid: bool = False

    prompt_tokens: int | None = None
    output_tokens: int | None = None
    thought_tokens: int | None = None
    finish_reason: str | None = None

    def as_row(self) -> dict:
        return {
            "mode": self.mode, "latency_ms": self.latency_ms, "api_ok": self.api_ok,
            "error_type": self.error_type,
            "raw_json_parsed": self.raw_json_parsed,
            "parsed_object_returned": self.parsed_object_returned,
            "native_schema_valid": self.native_schema_valid,
            "exact_enum_valid": self.exact_enum_valid,
            "coercion_applied": self.coercion_applied,
            "coercion_fields": sorted(self.coercion_fields),
            "repair_applied": self.repair_applied,
            "fallback_reason": self.fallback_reason,
            "final_schema_valid": self.final_schema_valid,
            "prompt_tokens": self.prompt_tokens, "output_tokens": self.output_tokens,
            "thought_tokens": self.thought_tokens, "finish_reason": self.finish_reason,
        }


ENUM_FIELDS = {
    "intent": {"identify_catch", "weather_query", "log_catch", "make_declaration", "other"},
    "confidence_label": {"low", "medium", "high"},
    "recommended_next_step": {"confirm_species", "retake_photo", "enter_measurement", "none"},
}


def enums_exactly_valid(raw: dict | None) -> bool:
    """True when every enum the model emitted was already a legal value."""
    if not isinstance(raw, dict):
        return False
    return all(raw.get(f) in allowed for f, allowed in ENUM_FIELDS.items())


def extract_json(text: str) -> dict | None:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, TypeError):
        pass
    m = _JSON_RE.search(text or "")
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def native_validate(raw: dict | None) -> GemmaTransportAnalysis | None:
    """Validate raw model output against the transport schema WITHOUT coercion."""
    if not isinstance(raw, dict):
        return None
    try:
        return GemmaTransportAnalysis(**raw)
    except Exception:  # noqa: BLE001 — invalidity is a measurement
        return None


def diff_fields(before: dict, after: dict) -> list[str]:
    """Fields whose value coercion changed — the transparency record."""
    changed = []
    for k in set(before) | set(after):
        if before.get(k) != after.get(k):
            changed.append(k)
    return sorted(changed)


# --------------------------------------------------------------------- config

def build_config(types, mode: str, *, system_instruction: str | None, tools=None,
                 thinking_level: str | None = None, max_output_tokens: int | None = None,
                 timeout_ms: int = 60_000, temperature: float = 0.2):
    """Build a GenerateContentConfig for one mode. Never mixes mechanisms."""
    kwargs: dict[str, Any] = {
        "temperature": temperature,
        "http_options": types.HttpOptions(timeout=timeout_ms),
    }
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    if tools is not None:
        kwargs["tools"] = [tools]
    if thinking_level:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
    if max_output_tokens:
        kwargs["max_output_tokens"] = max_output_tokens

    if mode == MODE_PYDANTIC:
        kwargs["response_mime_type"] = "application/json"
        kwargs["response_schema"] = GemmaTransportAnalysis
    elif mode == MODE_JSON_SCHEMA:
        kwargs["response_mime_type"] = "application/json"
        kwargs["response_json_schema"] = GemmaTransportAnalysis.model_json_schema()
    elif mode == MODE_PROMPT_FALLBACK:
        pass  # the schema is described in the prompt instead
    elif mode == MODE_INTERACTIONS:
        raise ValueError("interactions mode does not use GenerateContentConfig")
    else:
        raise ValueError(f"unknown structured-output mode: {mode}")
    return types.GenerateContentConfig(**kwargs)


def supports_mode(types, mode: str) -> tuple[bool, str | None]:
    """Can the INSTALLED SDK even build this config? (Client-side check only.)"""
    if mode == MODE_INTERACTIONS:
        return False, "not validated for this model; see docs/AI_STEP2_EXPERIMENT_PLAN.md"
    try:
        build_config(types, mode, system_instruction="x")
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {str(e)[:160]}"


def best_supported_mode(types, probed: dict[str, bool] | None = None) -> str:
    """Strongest mode that is supported client-side AND (if probed) server-side."""
    for mode in (MODE_PYDANTIC, MODE_JSON_SCHEMA, MODE_PROMPT_FALLBACK):
        ok, _ = supports_mode(types, mode)
        if not ok:
            continue
        if probed is not None and not probed.get(mode, False):
            continue
        return mode
    return MODE_PROMPT_FALLBACK


# --------------------------------------------------------------------- call

def call_structured(client, model: str, contents, config, mode: str,
                    allowed_ids: set[str]) -> tuple[StructuredCall, Any, dict | None]:
    """One structured-output attempt, fully instrumented.

    Returns (diagnostics, application_model_or_None, raw_dict_or_None). The
    caller owns repair and fallback decisions — this function measures, it does
    not paper over.
    """
    from app.schemas.gemma_gate import coerce_to_schema
    from app.schemas.transport import to_application_model

    diag = StructuredCall(mode=mode)
    t0 = time.monotonic()
    try:
        response = client.models.generate_content(model=model, contents=contents, config=config)
    except Exception as e:  # noqa: BLE001
        diag.latency_ms = int((time.monotonic() - t0) * 1000)
        diag.error_type = type(e).__name__
        diag.fallback_reason = "api_error"
        return diag, None, None

    diag.latency_ms = int((time.monotonic() - t0) * 1000)
    diag.api_ok = True

    um = getattr(response, "usage_metadata", None)
    if um is not None:
        diag.prompt_tokens = um.prompt_token_count
        diag.output_tokens = um.candidates_token_count
        diag.thought_tokens = um.thoughts_token_count
    cands = response.candidates or []
    if cands:
        diag.finish_reason = str(getattr(cands[0], "finish_reason", None))

    # 1. SDK-parsed result. Measured, not assumed: with response_json_schema this
    #    SDK populates `parsed` as a plain dict, and with response_schema it may
    #    stay None — so accept either shape and validate a dict ourselves.
    transport = None
    parsed_obj = getattr(response, "parsed", None)
    if isinstance(parsed_obj, GemmaTransportAnalysis):
        diag.parsed_object_returned = True
        transport = parsed_obj
    elif isinstance(parsed_obj, dict):
        diag.parsed_object_returned = True
        transport = native_validate(parsed_obj)

    text = response.text or ""
    raw = extract_json(text)
    if raw is None and isinstance(parsed_obj, dict):
        raw = parsed_obj
    diag.raw_json_parsed = raw is not None

    # 2. Native validity: does the RAW output satisfy the schema untouched?
    if transport is None:
        transport = native_validate(raw)
    diag.native_schema_valid = transport is not None
    diag.exact_enum_valid = enums_exactly_valid(raw)

    if transport is not None:
        app_model = to_application_model(transport, allowed_ids)
        diag.final_schema_valid = True
        # A species id outside the shortlist is dropped by the conversion; that
        # is an allow-list action, and it must still be reported honestly.
        if raw and (raw.get("species_suggestion") or {}).get("species_id") not in (
                None, app_model.species_suggestion.species_id):
            diag.coercion_applied = True
            diag.coercion_fields = ["species_suggestion.species_id"]
            diag.fallback_reason = "species_outside_shortlist"
        return diag, app_model, raw

    # 3. Not natively valid -> the Step-1 coercion boundary takes over.
    if raw is not None:
        before = dict(raw)
        app_model = coerce_to_schema(raw, allowed_ids)
        if app_model is not None:
            after = app_model.model_dump()
            diag.coercion_applied = True
            diag.coercion_fields = [f for f in diff_fields(
                {k: before.get(k) for k in ENUM_FIELDS},
                {k: after.get(k) for k in ENUM_FIELDS})]
            for f in ENUM_FIELDS:
                if before.get(f) not in ENUM_FIELDS[f] and f not in diag.coercion_fields:
                    diag.coercion_fields.append(f)
            diag.coercion_fields = sorted(set(diag.coercion_fields))
            diag.final_schema_valid = True
            diag.fallback_reason = "native_schema_invalid"
            return diag, app_model, raw

    diag.fallback_reason = "unparseable_output"
    return diag, None, raw
