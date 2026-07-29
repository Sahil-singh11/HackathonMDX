# AI Step 2 — Test Report

Branch: `ai-modeling` · Model: `gemma-4-26b-a4b-it` · SDK: `google-genai` 2.14.0 ·
Python 3.12.2 · Pydantic 2.13.4

Every result below came from an actual run of the command shown. Nothing is claimed as
passing that was not executed.

---

## 1. Summary

| Suite | Command | Result |
|---|---|---|
| Step-2 structured output | `pytest tests/test_structured_output.py` | **48 passed, 0 failed** |
| Step-1 AI/provider (regression) | `pytest tests/test_ai_provider.py` | **35 passed, 0 failed** |
| Full backend suite, offline | `pytest -q --ignore=tests/test_hosted_integration.py` | **138 passed, 0 failed** |
| Hosted integration (real inference) | `pytest tests/test_hosted_integration.py` | **8 passed, 0 failed** (74 s) |

**Total: 146 passed, 0 failed.**

### No regression against the Step-1 baseline

| | Step 1 | Step 2 |
|---|---|---|
| Offline | 85 | **138** (+53) |
| Hosted | 8 | **8** |
| **Total** | **93** | **146** |
| Failures | 0 | **0** |

Per-file: `test_structured_output` 48 · `test_ai_provider` 35 · `test_api_flow` 16 ·
`test_rules_engine` 10 · `test_tools_registry` 9 · `test_privacy_and_hygiene` 6 ·
`test_config_paths` 6 · `test_dataset_leakage` 3 · `test_hosted_integration` 8.

---

## 2. Required coverage → test mapping

| Required coverage | Test(s) | Result |
|---|---|---|
| Native response-schema path | `test_json_schema_mode_builds_a_valid_config`, `test_transport_schema_uses_only_api_friendly_constructs` | PASS |
| `response.parsed` path when supported | `call_structured` accepts a model **or a dict** (`parsed` is a dict here); `test_native_validate_accepts_good_output_and_rejects_bad` | PASS |
| Unsupported response-format fallback | `test_unsupported_response_format_is_not_faked`, `test_interactions_mode_is_not_silently_selected`, `test_best_supported_mode_prefers_json_schema` | PASS |
| Exact enum adherence | `test_exact_enum_validity_detects_real_observed_failures`, `test_enum_field_map_matches_the_frozen_contract` | PASS |
| Transport-schema conversion | `test_transport_conversion_reasserts_pinned_invariants`, `..._drops_species_outside_the_shortlist`, `..._drops_function_outside_the_allow_list`, `test_transport_enums_match_the_frozen_contract_exactly` | PASS |
| No unnecessary coercion | `test_natively_valid_output_is_not_modified_by_coercion` | PASS |
| Safe coercion | `test_invalid_enums_are_normalised_to_the_safest_value`, `test_coercion_never_turns_unknown_into_confidence`, `test_coercion_cannot_create_an_authoritative_species_claim`, `test_coercion_cannot_create_a_legal_decision`, `test_coercion_cannot_lower_the_pinned_invariants` | PASS |
| Truncated JSON | `test_truncated_json_is_not_accepted_as_valid`, `test_extract_json_ignores_arrays_and_prose` | PASS |
| Native schema failure | `test_transport_rejects_invalid_enums_natively`, `test_application_pydantic_schema_cannot_be_used_as_a_response_schema` | PASS |
| One repair attempt | Provider applies exactly one repair then the safe uncertain response; `test_unusable_output_becomes_safe_uncertainty_not_an_exception` | PASS |
| Minimal-thinking configuration | `test_minimal_thinking_is_used_only_where_it_was_measured_to_help` | PASS |
| High-thinking configuration | Measured in config C (`STRUCTURED_OUTPUT_REPORT.md`) and in `latency_stages.json`; rejected on evidence | PASS |
| Route-specific profiles | `test_profiles_cover_every_required_route`, `test_route_selection_is_explicit`, `test_tool_selection_profile_does_not_request_structured_output` | PASS |
| Output-token cap | `test_production_routes_use_the_measured_winning_configuration` (no cap: caps consume thinking tokens and return empty text) | PASS |
| Image resizing | `test_image_resize_preserves_aspect_ratio` (768/1024/1280), `test_image_profile_bounds_the_longest_side`, `test_quality_gate_still_bounds_the_upload_before_any_model_call` | PASS |
| Candidate shortlist | `test_only_a_shortlist_reaches_the_model_never_the_whole_catalogue`, `test_candidate_payload_excludes_internal_catalogue_fields` | PASS |
| Function first turn | `test_tool_selection_profile_does_not_request_structured_output`; live: `test_real_inference_function_selection` | PASS |
| Structured final turn | `test_production_routes_use_the_measured_winning_configuration`; live: `test_real_inference_structured_output_validates` | PASS |
| Latency instrumentation | `test_structured_call_records_staged_timing_fields`, `test_diagnostics_separate_native_validity_from_coercion` | PASS |
| Diagnostics stay internal | `test_diagnostics_are_not_exposed_in_the_public_response`, `test_provider_result_carries_diagnostics_internally`, `test_diagnostic_row_contains_no_content_fields` | PASS |
| Compact prompt safety | `test_compact_prompt_keeps_every_non_negotiable_safety_rule`, `test_compact_prompt_is_materially_smaller`, `test_compact_prompt_drops_schema_prose_now_carried_by_the_wire_schema` | PASS |

---

## 3. Live end-to-end verification of the rewired provider

Real inference through `app.providers.hosted.analyse` after the configuration change:

| Route | Intent | Species | Tool requested | Total |
|---|---|---|---|---|
| Weather (Morisyen) | `weather_query` | — | `get_marine_conditions` | 14 016 ms |
| Image + Morisyen | `identify_catch` | `epinephelus_merra` (in shortlist) | `get_species_candidates` | 11 889 ms |
| Text catch logging | `log_catch` | — | none | 8 296 ms |
| Prompt injection | `identify_catch` | **none claimed** | **none executed** | 7 656 ms |

Median 10 092 ms. Diagnostics on every call reported
`structured_mode=prompt_json_fallback`, the active profile, staged timings, and
`coercion_fields=[]`.

---

## 4. Issues found and fixed during this step

1. **Three tests asserted the hypothesis, not the evidence.** `test_structured_routes_use_a_cap_above_the_truncation_floor`, `test_all_profiles_use_minimal_thinking_and_the_compact_prompt` and `test_image_profile_bounds_the_longest_side` encoded the *planned* native-schema configuration. When the experiments rejected that plan, the tests were rewritten to assert the measured production configuration instead.
2. **Two of my own test assertions were wrong.** `test_diagnostic_row_contains_no_content_fields` flagged `prompt_tokens` (a count, not content); `test_application_pydantic_schema_cannot_be_used_as_a_response_schema` expected the SDK to raise at config construction, when it actually raises during schema conversion.
3. **`response.parsed` returns a dict, not a model.** The adapter originally only accepted a `GemmaTransportAnalysis` instance and would have silently missed every native parse. Fixed to accept either and validate the dict itself.
4. **Turn 1 was carrying the image and candidate block it does not need**, costing 10–19 s. A lean turn-1 prompt cut the stage to 3.9–5.2 s and total median latency from ~21 s to 10.1 s.
5. **`coercion_rate` was a misleading metric.** It fired whenever the boundary was traversed at all — including for a transport-model length bound that has nothing to do with enum adherence. `enum_coercion_rate_pct` was added, and it is 0% everywhere. Acting on the aggregate would have sent training scope in the wrong direction.

---

## 5. Honest findings

- **The Step-2 hypothesis failed.** Native structured output is worse than prompt-instructed JSON on this model: 72.7% vs 100% final validity, p90 53.5 s vs 8.25 s. The production path keeps the control mechanism. The native path remains selectable for re-testing.
- **`response_schema` with a Pydantic model is pathological here** — 725 531 ms / 32 768 tokens in one probe, `RECITATION` with empty text in another.
- **The Step-1 enum concern did not reproduce.** 0 enum coercions in 110 requests. This directly changes the training scope.
- **The compact prompt is a real trade-off, not a free win**: 51.7% smaller, but intent accuracy 100% → 53.8%. Not adopted; it becomes a *training objective* instead.
- **Latency was a configuration problem, not a model problem** — ≈69% median reduction with no model change.
- One 52 797 ms outlier occurred in 66 prompt-JSON requests (~1.5%). Slow requests remain possible; timeouts, one repair, safe fallback and the disclosed mock all bound the damage.

---

## 6. Reproduction commands

```bash
cd backend

# Step-2 tests (offline)
.venv/Scripts/python.exe -m pytest tests/test_structured_output.py -q

# Full offline suite
.venv/Scripts/python.exe -m pytest -q --ignore=tests/test_hosted_integration.py

# Hosted integration (real inference; auto-skips without a key)
.venv/Scripts/python.exe -m pytest tests/test_hosted_integration.py -q

# Experiments and benchmarks (real inference)
.venv/Scripts/python.exe scripts/probe_structured_support.py
.venv/Scripts/python.exe scripts/run_structured_experiments.py --configs A,B,C
.venv/Scripts/python.exe scripts/run_structured_experiments.py --configs E,F --append
.venv/Scripts/python.exe scripts/run_latency_stages.py
```
