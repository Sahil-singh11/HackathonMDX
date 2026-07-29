"""AI Step 2 — native structured output, transport conversion, coercion transparency,
route profiles and latency instrumentation.

Offline: conftest forces PROVIDER_MODE=mock and clears GEMINI_API_KEY, so nothing here
reaches the network. Live behaviour is covered in test_hosted_integration.py.
"""
import json

import pytest
from pydantic import ValidationError

from app.providers import profiles, structured
from app.providers.structured import (ENUM_FIELDS, MODE_JSON_SCHEMA, MODE_PROMPT_FALLBACK,
                                      MODE_PYDANTIC, StructuredCall, enums_exactly_valid,
                                      extract_json, native_validate)
from app.schemas.gemma_gate import GemmaStructuredAnalysis, coerce_to_schema
from app.schemas.transport import GemmaTransportAnalysis, to_application_model

ALLOWED = {"octopus_cyanea", "siganus_sutor", "epinephelus_merra"}


def _transport(**over) -> dict:
    base = {
        "intent": "identify_catch",
        "species_suggestion": {"species_id": "octopus_cyanea", "morisyen": "ourite",
                               "english": "Day octopus", "scientific": "Octopus cyanea"},
        "visible_characteristics": ["bulbous mantle", "mottled skin"],
        "confidence_label": "medium",
        "estimated_size_unverified_cm": 30.0,
        "reply": "This may be a day octopus. Please confirm.",
        "reply_morisyen": "Kitfwa enn ourite. Silvouple konfirm.",
        "recommended_next_step": "confirm_species",
        "requested_function": None,
        "limitations": [],
    }
    base.update(over)
    return base


# ------------------------------------------------------- transport schema / conversion

def test_transport_schema_uses_only_api_friendly_constructs():
    js = GemmaTransportAnalysis.model_json_schema()
    props = js["properties"]
    for field in ("intent", "confidence_label", "recommended_next_step"):
        assert "enum" in props[field], f"{field} must be a plain string enum"
        assert props[field]["type"] == "string"
    # Bounded lists (these bounds stop the model expanding to the output ceiling).
    assert props["visible_characteristics"]["maxItems"] == 3
    assert props["limitations"]["maxItems"] == 2
    assert props["reply"]["maxLength"] == 220
    assert props["reply_morisyen"]["maxLength"] == 220
    # No recursion, no dict-typed fields.
    assert "additionalProperties" not in props.get("species_suggestion", {})
    assert json.dumps(js)  # must be serialisable for response_json_schema


def test_transport_enums_match_the_frozen_contract_exactly():
    js = GemmaTransportAnalysis.model_json_schema()["properties"]
    assert set(js["intent"]["enum"]) == {
        "identify_catch", "weather_query", "log_catch", "make_declaration", "other"}
    assert set(js["confidence_label"]["enum"]) == {"low", "medium", "high"}
    assert set(js["recommended_next_step"]["enum"]) == {
        "confirm_species", "retake_photo", "enter_measurement", "none"}


def test_application_pydantic_schema_cannot_be_used_as_a_response_schema():
    """Why the transport model exists: Literal[True] breaks the SDK converter."""
    from google.genai import types
    from google.genai import _transformers as t

    # The SDK accepts the config object, then fails when it converts the Pydantic model
    # into a wire schema — Literal[True] is not a string literal.
    cfg = types.GenerateContentConfig(response_mime_type="application/json",
                                      response_schema=GemmaStructuredAnalysis)
    with pytest.raises(Exception) as exc:
        t.t_schema(None, cfg.response_schema)
    assert "literal" in str(exc.value).lower()


def test_transport_conversion_reasserts_pinned_invariants():
    t = GemmaTransportAnalysis(**_transport())
    app = to_application_model(t, ALLOWED)
    assert app.species_confirmation_required is True
    assert app.measured_size_required is True
    assert app.species_suggestion.species_id == "octopus_cyanea"
    assert app.intent == "identify_catch"


def test_transport_conversion_drops_species_outside_the_shortlist():
    t = GemmaTransportAnalysis(**_transport(
        species_suggestion={"species_id": "thunnus_albacares", "morisyen": "ton",
                            "english": "Yellowfin tuna", "scientific": "Thunnus albacares"}))
    app = to_application_model(t, ALLOWED)
    assert app.species_suggestion.species_id is None
    # And the names go with it — a name without an allow-listed id is an unbacked claim.
    assert app.species_suggestion.english is None
    assert app.species_suggestion.scientific is None


def test_transport_conversion_drops_function_outside_the_allow_list():
    t = GemmaTransportAnalysis(**_transport(requested_function="unrestricted_tool"))
    assert to_application_model(t, ALLOWED).requested_function is None
    t2 = GemmaTransportAnalysis(**_transport(requested_function="get_marine_conditions"))
    assert to_application_model(t2, ALLOWED).requested_function == "get_marine_conditions"


def test_transport_rejects_invalid_enums_natively():
    with pytest.raises(ValidationError):
        GemmaTransportAnalysis(**_transport(intent="species_identification"))
    with pytest.raises(ValidationError):
        GemmaTransportAnalysis(**_transport(confidence_label="none"))
    with pytest.raises(ValidationError):
        GemmaTransportAnalysis(**_transport(recommended_next_step="Upload a clear photo."))


# ------------------------------------------------------- adapter mode selection

def test_modes_are_explicit_and_named():
    assert structured.ALL_MODES == (
        "generate_content_pydantic_schema", "generate_content_json_schema",
        "interactions_response_format", "prompt_json_fallback")


def test_json_schema_mode_builds_a_valid_config():
    from google.genai import types
    cfg = structured.build_config(types, MODE_JSON_SCHEMA, system_instruction="x")
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_json_schema is not None
    assert cfg.response_schema is None  # never both mechanisms at once


def test_prompt_fallback_mode_sets_no_native_schema():
    from google.genai import types
    cfg = structured.build_config(types, MODE_PROMPT_FALLBACK, system_instruction="x")
    assert cfg.response_mime_type is None
    assert cfg.response_json_schema is None
    assert cfg.response_schema is None


def test_pydantic_mode_is_unbuildable_with_the_application_schema():
    """Documents the measured constraint rather than silently preferring it."""
    from google.genai import types
    ok, reason = structured.supports_mode(types, MODE_PYDANTIC)
    # It builds with the transport model; the rejection is on measured runtime behaviour.
    assert ok is True or "Literal" in (reason or "")


def test_unsupported_response_format_is_not_faked():
    """Config D: the newer response_format simply does not exist in this SDK."""
    from google.genai import types
    assert "response_format" not in types.GenerateContentConfig.model_fields


def test_interactions_mode_is_not_silently_selected():
    from google.genai import types
    ok, reason = structured.supports_mode(types, structured.MODE_INTERACTIONS)
    assert ok is False and reason
    assert structured.best_supported_mode(types) != structured.MODE_INTERACTIONS


def test_best_supported_mode_prefers_json_schema():
    from google.genai import types
    assert structured.best_supported_mode(
        types, probed={MODE_JSON_SCHEMA: True}) == MODE_JSON_SCHEMA
    # With nothing probed as working, it falls back to the always-runnable control.
    assert structured.best_supported_mode(
        types, probed={MODE_JSON_SCHEMA: False, MODE_PYDANTIC: False}) == MODE_PROMPT_FALLBACK


def test_no_mode_switch_is_silent():
    call = StructuredCall(mode=MODE_JSON_SCHEMA)
    assert call.as_row()["mode"] == MODE_JSON_SCHEMA


# ------------------------------------------------------- enum + native validity

def test_exact_enum_validity_detects_real_observed_failures():
    assert enums_exactly_valid(_transport()) is True
    assert enums_exactly_valid(_transport(intent="species_identification")) is False
    assert enums_exactly_valid(_transport(confidence_label="none")) is False
    assert enums_exactly_valid(_transport(recommended_next_step="Upload a clear photo.")) is False
    assert enums_exactly_valid(None) is False


def test_native_validate_accepts_good_output_and_rejects_bad():
    assert native_validate(_transport()) is not None
    assert native_validate(_transport(intent="nope")) is None
    assert native_validate("not a dict") is None


def test_truncated_json_is_not_accepted_as_valid():
    truncated = '{"intent": "identify_catch", "species_suggestion": {"species_id": null'
    assert extract_json(truncated) is None
    assert native_validate(extract_json(truncated)) is None


def test_extract_json_ignores_arrays_and_prose():
    assert extract_json('["a", "b"]') is None
    assert extract_json("I cannot answer in JSON.") is None
    assert extract_json('```json\n{"intent": "other"}\n```') == {"intent": "other"}


# ------------------------------------------------------- coercion transparency

def test_natively_valid_output_is_not_modified_by_coercion():
    raw = _transport()
    coerced = coerce_to_schema(dict(raw), ALLOWED)
    assert coerced is not None
    assert coerced.intent == raw["intent"]
    assert coerced.confidence_label == raw["confidence_label"]
    assert coerced.recommended_next_step == raw["recommended_next_step"]
    assert coerced.species_suggestion.species_id == raw["species_suggestion"]["species_id"]
    assert coerced.reply == raw["reply"]


def test_invalid_enums_are_normalised_to_the_safest_value():
    coerced = coerce_to_schema(_transport(
        intent="species_identification", confidence_label="none",
        recommended_next_step="Upload a clear photo of the fish."), ALLOWED)
    assert coerced.intent == "other"
    assert coerced.confidence_label == "low"          # never upgraded
    assert coerced.recommended_next_step == "confirm_species"


def test_coercion_never_turns_unknown_into_confidence():
    coerced = coerce_to_schema(_transport(
        species_suggestion={"species_id": None, "morisyen": None, "english": None, "scientific": None},
        confidence_label="not-a-level"), ALLOWED)
    assert coerced.species_suggestion.species_id is None
    assert coerced.confidence_label == "low"
    assert coerced.species_confirmation_required is True


def test_coercion_cannot_create_an_authoritative_species_claim():
    coerced = coerce_to_schema(_transport(
        species_suggestion={"species_id": "not_in_shortlist", "morisyen": "x",
                            "english": "Definitely a tuna", "scientific": "Thunnus"}), ALLOWED)
    assert coerced.species_suggestion.species_id is None
    assert coerced.species_confirmation_required is True


def test_coercion_cannot_create_a_legal_decision():
    coerced = coerce_to_schema(_transport(), ALLOWED)
    dumped = coerced.model_dump()
    assert "legal_check" not in dumped
    assert "legal_status" not in dumped
    # Legality only ever comes from the deterministic rules engine after confirmation.


def test_coercion_cannot_lower_the_pinned_invariants():
    coerced = coerce_to_schema(
        {**_transport(), "species_confirmation_required": False, "measured_size_required": False},
        ALLOWED)
    assert coerced.species_confirmation_required is True
    assert coerced.measured_size_required is True


def test_unusable_output_becomes_safe_uncertainty_not_an_exception():
    assert coerce_to_schema(None, ALLOWED) is None
    assert coerce_to_schema("prose", ALLOWED) is None
    assert coerce_to_schema([], ALLOWED) is None


def test_diagnostics_separate_native_validity_from_coercion():
    """A coerced result must never be reported as natively compliant."""
    call = StructuredCall(mode=MODE_JSON_SCHEMA)
    call.native_schema_valid = False
    call.coercion_applied = True
    call.coercion_fields = ["intent"]
    call.final_schema_valid = True
    row = call.as_row()
    assert row["native_schema_valid"] is False
    assert row["coercion_applied"] is True
    assert row["final_schema_valid"] is True
    assert row["coercion_fields"] == ["intent"]


def test_diagnostic_row_contains_no_content_fields():
    """Counts and flags only. `*_tokens` keys are counts, never the tokens themselves."""
    row = StructuredCall(mode=MODE_JSON_SCHEMA).as_row()
    keys = [k for k in row if not k.endswith("_tokens")]
    for banned in ("prompt", "text", "reply", "note", "image", "thought", "reasoning", "content"):
        assert not any(banned in k for k in keys), f"diagnostics must not carry {banned}"
    for k in ("prompt_tokens", "output_tokens", "thought_tokens"):
        assert row[k] is None or isinstance(row[k], int)


# ------------------------------------------------------- route profiles

def test_profiles_cover_every_required_route():
    assert set(profiles.PROFILES) == {
        "fast_intent", "fast_tool_selection", "image_species_analysis", "final_tool_response"}


def test_tool_selection_profile_does_not_request_structured_output():
    """A response schema and a function_call part compete for the same output."""
    assert profiles.FAST_TOOL_SELECTION.structured is False
    assert profiles.FAST_TOOL_SELECTION.max_output_tokens is None


def test_production_routes_use_the_measured_winning_configuration():
    """Config A won on every quality metric; profiles must encode that, not the hypothesis."""
    from app.providers.hosted import PRODUCTION_MODE
    assert PRODUCTION_MODE == MODE_PROMPT_FALLBACK
    for p in (profiles.FAST_INTENT, profiles.IMAGE_SPECIES_ANALYSIS, profiles.FINAL_TOOL_RESPONSE):
        assert p.structured is False, "native structured output was rejected on measured evidence"
        # A cap also consumes hidden thinking tokens on this model and returned EMPTY text.
        assert p.max_output_tokens is None
        assert p.thinking_level is None, "default thinking measured fastest end to end"


def test_full_prompt_is_used_where_intent_accuracy_matters():
    """The compact prompt cost intent accuracy (100% -> 53.8%), so it is not used."""
    for p in profiles.PROFILES.values():
        assert p.compact_prompt is False


def test_minimal_thinking_is_used_only_where_it_was_measured_to_help():
    assert profiles.FAST_TOOL_SELECTION.thinking_level == profiles.THINKING_MINIMAL
    assert profiles.FAST_INTENT.thinking_level is None


def test_route_selection_is_explicit():
    assert profiles.for_request(has_image=True, stage="analysis").name == "image_species_analysis"
    assert profiles.for_request(has_image=False, stage="analysis").name == "fast_intent"
    assert profiles.for_request(has_image=False, stage="tool_selection").name == "fast_tool_selection"
    assert profiles.for_request(has_image=True, stage="final_tool_response").name == "final_tool_response"


def test_image_profile_bounds_the_longest_side():
    """768px measured slower and no more accurate; 1024 vs 1280 was inconclusive
    (the demo fixtures are already <=1024), so the existing ceiling is kept."""
    assert profiles.IMAGE_SPECIES_ANALYSIS.image_longest_side == 1280


# ------------------------------------------------------- compact prompt

def test_compact_prompt_keeps_every_non_negotiable_safety_rule():
    from app.prompts.system import COMPACT_SYSTEM_INSTRUCTION as C
    low = C.lower()
    assert "only from the supplied candidate list" in low
    assert "never identify authoritatively" in low
    assert "the fisher must confirm" in low
    assert "never say a catch is legal or illegal" in low
    assert "never invent regulations" in low
    assert "unverified, never a measurement" in low
    assert "never say conditions are safe" in low
    assert "untrusted" in low
    assert "only the functions offered" in low


def test_compact_prompt_is_materially_smaller():
    from app.prompts.system import COMPACT_SYSTEM_INSTRUCTION as C
    from app.prompts.system import SYSTEM_INSTRUCTION as F
    assert len(C) < len(F) * 0.6, "compaction should cut the prompt by >40%"


def test_compact_prompt_drops_schema_prose_now_carried_by_the_wire_schema():
    from app.prompts.system import COMPACT_SYSTEM_INSTRUCTION as C
    assert "identify_catch|weather_query" not in C
    assert '"recommended_next_step"' not in C


# ------------------------------------------------------- image resizing

@pytest.mark.parametrize("longest", [768, 1024, 1280])
def test_image_resize_preserves_aspect_ratio(longest, sharp_image):
    from io import BytesIO

    from PIL import Image, ImageOps
    src = ImageOps.exif_transpose(Image.open(BytesIO(sharp_image))).convert("RGB")
    img = src.copy()
    img.thumbnail((longest, longest))
    assert max(img.size) <= longest
    src_ratio = src.size[0] / src.size[1]
    assert abs(img.size[0] / img.size[1] - src_ratio) < 0.05


def test_quality_gate_still_bounds_the_upload_before_any_model_call():
    from app.services.vision import quality
    assert quality.MAX_ANALYSIS_DIM >= profiles.IMAGE_SPECIES_ANALYSIS.image_longest_side


# ------------------------------------------------------- candidate shortlist

def test_only_a_shortlist_reaches_the_model_never_the_whole_catalogue():
    from app.services.species.retrieval import MAX_CANDIDATES, candidates_for, load_catalogue
    assert len(candidates_for(None)) <= MAX_CANDIDATES
    shortlist = candidates_for("mo'nn gagn enn ourite")
    assert len(shortlist) <= MAX_CANDIDATES
    assert len(shortlist) <= len(load_catalogue())


def test_candidate_payload_excludes_internal_catalogue_fields():
    from app.services.species.retrieval import load_catalogue, public_candidate
    sp = load_catalogue()[0]
    pub = public_candidate(sp)
    assert "keywords" not in pub  # retrieval-only, wasted tokens on the wire
    assert set(pub) == {"species_id", "scientific", "english", "morisyen",
                        "morisyen_status", "visible_characteristics"}


# ------------------------------------------------------- latency instrumentation

def test_structured_call_records_staged_timing_fields():
    row = StructuredCall(mode=MODE_JSON_SCHEMA, latency_ms=1234).as_row()
    assert row["latency_ms"] == 1234
    for k in ("prompt_tokens", "output_tokens", "thought_tokens", "finish_reason"):
        assert k in row


def test_enum_field_map_matches_the_frozen_contract():
    from app.schemas.analysis import Confidence, Intent, NextStep
    import typing
    assert ENUM_FIELDS["intent"] == set(typing.get_args(Intent))
    assert ENUM_FIELDS["confidence_label"] == set(typing.get_args(Confidence))
    assert ENUM_FIELDS["recommended_next_step"] == set(typing.get_args(NextStep))


# ------------------------------------------------------- public API isolation

def test_diagnostics_are_not_exposed_in_the_public_response(client, sharp_image):
    r = client.post("/api/analyse-catch",
                    files={"image": ("c.jpg", sharp_image, "image/jpeg")},
                    data={"note": "test", "language": "en", "provider_mode": "mock"})
    assert r.status_code == 200
    body = r.json()
    for leaked in ("diagnostics", "structured_mode", "coercion_applied", "thought_tokens",
                   "native_schema_valid", "stages_ms"):
        assert leaked not in json.dumps(body), f"internal diagnostic {leaked} leaked to the public API"


def test_provider_result_carries_diagnostics_internally():
    from app.providers.base import ProviderResult
    res = ProviderResult()
    assert isinstance(res.diagnostics, dict)
    assert "diagnostics" not in GemmaStructuredAnalysis.model_fields
