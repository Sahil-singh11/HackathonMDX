# AI Step 3 — Test Report

Branch: `ai-modeling` · Base model: `google/gemma-4-E2B-it` · Assessed 2026-07-29 MUT

Every result below came from an actual run of the command shown. Nothing is claimed as
passing that was not executed.

---

## 1. Summary

| Suite | Command | Result |
|---|---|---|
| Step-3 dataset / prompt / router | `pytest tests/test_step3_training.py` | **46 passed, 0 failed** |
| Full backend suite, offline | `pytest -q --ignore=tests/test_hosted_integration.py` | **184 passed, 0 failed** |
| Hosted integration (real inference) | `pytest tests/test_hosted_integration.py` | see §5 |

### No regression against the Step-2 baseline

| | Step 2 | Step 3 |
|---|---|---|
| Offline | 138 | **184** (+46) |
| Hosted | 8 | 8 |
| **Total** | **146** | **192** |
| Failures | 0 | **0** |

## 2. Dataset validation gates

All five run against the committed dataset; reports in `training/results/`.

| Check | Script | Result |
|---|---|---|
| Schema, ids, enums, secrets, duplicates | `validate_training_dataset.py` | **PASS** |
| External-test immutability + cross-split near-duplicates | `check_training_leakage.py` | **PASS** |
| Semantic-family split integrity | `check_semantic_family_split.py` | **PASS** |
| Tool names + arguments vs the live registry | `check_tool_arguments.py` | **PASS** |
| No unsafe training target | `check_training_safety.py` | **PASS** |

## 3. Required coverage → test mapping

| Required coverage | Test(s) | Result |
|---|---|---|
| Dataset schema | `test_every_record_has_every_required_field`, `test_record_ids_are_unique`, `test_intents_and_tools_are_from_the_frozen_vocabulary`, `test_provenance_vocabulary_is_closed` | PASS |
| Semantic-family splitting | `test_no_semantic_family_spans_two_splits`, `test_split_ratios_are_close_to_70_15_15`, `test_split_files_reconstruct_the_master`, `test_every_split_covers_every_intent` | PASS |
| External-test immutability | `test_external_benchmark_matches_its_manifest_checksum`, `test_external_cases_are_not_in_any_split_file` | PASS |
| Leakage | `test_no_training_record_copies_an_external_case`, `test_no_training_record_shares_a_four_word_run_with_an_external_case` | PASS |
| Compact prompt | `test_compact_prompt_checksum_matches_the_frozen_config`, `test_compact_prompt_keeps_every_non_negotiable_safety_rule`, `test_compact_prompt_is_materially_smaller_than_the_full_prompt`, `test_compact_prompt_carries_no_worked_examples`, `test_compact_prompt_lists_every_intent` | PASS |
| Model chat formatting | `test_router_uses_the_frozen_compact_prompt_verbatim`; notebook asserts the official `chat_template.jinja` loaded (18 567 chars) before formatting | PASS |
| Adapter loading | `test_router_provider_is_not_available_without_an_accepted_adapter` | PASS |
| Untuned evaluation | notebook §8 (`evaluate` + `summarise`), run on the internal test and the immutable benchmark | see §5 |
| Tuned evaluation | notebook §12, identical code path as untuned | see §5 |
| Invalid tool | `test_router_validation_rejects_unknown_intent_and_tool`, `test_unknown_function_requests_never_select_a_tool` | PASS |
| Malformed arguments | `test_concrete_arguments_validate_against_the_real_registry_models`, `test_negative_argument_cases_are_present` | PASS |
| Prompt injection | `test_prompt_injection_records_exist_in_the_dataset` | PASS |
| Safe uncertainty | `test_router_validation_handles_unparseable_output_safely`, `test_invariants_are_never_lowerable_in_any_target` | PASS |
| No invented laws | `test_no_record_teaches_an_invented_rule`, `test_no_record_teaches_a_legal_verdict` | PASS |
| No marine guarantee | `test_no_record_teaches_a_marine_safety_guarantee` | PASS |
| Provider metadata | `test_router_provider_never_claims_out_of_scope_responsibility` | PASS |
| Router fallback | `test_router_route_raises_rather_than_falling_back_silently`, `test_router_is_not_a_default_provider_mode` | PASS |

## 4. Issues found by these tests (and fixed)

1. **`record_catch` requires `species_id`, which the router cannot know.**
   `check_tool_arguments.py` rejected six records that passed only `count`. The fisher who
   says "log two fish" has not named a species — it comes from the analysis they already
   confirmed. Fixed by encoding an explicit *context-supplied* argument set rather than
   teaching the router to invent a species, which the safety rules forbid.

2. **Eight training records overlapped the immutable benchmark.**
   `check_training_leakage.py` flagged shared four-word runs (`"met sa dan mo"`,
   `"ek donn mwa enn"`, `"ki mo bizin fer"`, `"mo pa nn mezir"`, `"dir mwa si li"`) plus one
   0.80-similarity record. Four cross-split near-duplicates were also caught. **All fixed in
   the data**; no threshold was relaxed.

3. **Provenance was overstated, and it hid safety records from review.**
   `test_review_queue_prioritises_safety_and_ambiguity` failed with 0 safety records queued.
   Root cause: 48 records were labelled `team_authored`, which marks them
   `human_review_status = not_required` — but an AI assistant authored them. Relabelled all
   240 to `AI_generated_review_required` / `pending`. The queue now contains 8
   safety-critical records, and the dataset card states the label `team_authored` is
   deliberately unused.

## 5. Kaggle training runs — what actually happened

Four kernel versions were pushed. The first three failed; each failure was diagnosed from
the real log and fixed rather than worked around.

| Version | Result | Cause | Fix |
|---|---|---|---|
| v1 | ERROR | `ValueError: checkpoint has model type gemma4 but Transformers does not recognize this architecture` — Kaggle's base image is too old | Dependency-upgrade cell that runs **before** any `transformers` import, plus an explicit `CONFIG_MAPPING_NAMES` check so a stale version fails loudly. Result: transformers 5.14.1, `gemma4 registered: True` |
| v3 | ERROR | Kernel **died**: `Error named symbol not found ... /src/csrc/ops.cu`. Kaggle allocated a **Tesla P100 (sm_60)**; bitsandbytes 4-bit NF4 needs sm_75+ and kills the process rather than raising | Detect compute capability; use 4-bit QLoRA only on sm_75+, otherwise plain LoRA in fp16 with a non-bitsandbytes optimiser. bf16 trusted only on sm_80+ |
| v5 | ERROR | Adaptive path worked (model loaded unquantised in fp16), then `AcceleratorError: CUDA error: no kernel image is available for execution on the device` — **torch 2.10+cu128 ships no compiled kernels for sm_60 at all**. `machine_shape: gpu-t4x2` was silently ignored | Correct enum value is `NvidiaTeslaT4` (per `kagglesdk`), not `gpu-t4x2` |
| v7 | see `docs/AI_STEP3_TRAINING_REPORT.md` | — | — |

Confirmed working before those failures, on every run: GPU attached, model access
(`gated: false`, no HF token needed), dataset loaded (240 / 170 / 36 / 34 + 32 external),
in-notebook leakage guard passed (worst train-vs-held-out similarity **0.769**), frozen
compact-prompt checksum matched (`44299533f59cc907`), official chat template loaded.

## 6. Reproduction

```bash
# dataset gates
python scripts/validate_training_dataset.py
python scripts/check_training_leakage.py
python scripts/check_semantic_family_split.py
python scripts/check_tool_arguments.py
python scripts/check_training_safety.py

# tests
cd backend
.venv/Scripts/python.exe -m pytest tests/test_step3_training.py -q
.venv/Scripts/python.exe -m pytest -q --ignore=tests/test_hosted_integration.py
.venv/Scripts/python.exe -m pytest tests/test_hosted_integration.py -q

# Kaggle
pwsh scripts/kaggle_push_ai_dataset.ps1
pwsh scripts/kaggle_push_ai_training.ps1
pwsh scripts/kaggle_monitor_ai_training.ps1
pwsh scripts/kaggle_download_ai_outputs.ps1
```
