# AI Step 4 — Test Report

Branch: `ai-modeling` · 2026-07-30 MUT

Every result below came from an actual run of the command shown. Nothing is claimed as
passing that was not executed.

---

## 1. Summary

| Suite | Command | Result |
|---|---|---|
| Step-4 review/v2/gates/routing | `pytest tests/test_step4_v2.py` | **52 passed, 0 failed** |
| Full backend suite, offline | `pytest -q --ignore=tests/test_hosted_integration.py` | **236 passed, 0 failed** |
| Hosted integration (real inference) | `pytest tests/test_hosted_integration.py` | **8 passed, 0 failed** (77 s) |

### No regression against the Step-3 baseline

| | Step 3 | Step 4 |
|---|---|---|
| Offline | 184 | **236** (+52) |
| Hosted | 8 | **8** |
| **Total** | **192** | **244** |
| Failures | 0 | **0** |

## 2. Dataset validators (v2 + challenge set)

`scripts/validate_v2_dataset.py` — all five gates **PASS** on the committed dataset:
schema · leakage (external + challenge + cross-split) · semantic families · tool arguments
vs the live registry · safety targets. Reports in `training/results/v2_*.json`.

## 3. Required coverage → test mapping (all PASS)

| Required coverage | Test(s) |
|---|---|
| Approved-review propagation | `test_approved_review_reached_the_dataset`, `test_review_block_records_who_and_how`, `test_review_csv_matches_what_was_applied`, `test_unreviewed_records_are_still_marked_unreviewed` |
| Reviewed wording preservation | `test_reviewed_wording_is_byte_identical_to_the_pre_review_dataset`, `test_review_does_not_claim_native_speaker_verification` |
| v1 archive immutability | `test_v1_archive_exists_with_manifest_and_checksums`, `test_v1_archive_checksums_still_verify`, `test_v1_step3_decision_is_preserved_unchanged`, `test_v1_adapter_weights_are_not_committed` |
| v2 dataset validation | `test_v2_size_is_in_the_target_range`, `test_v2_added_between_80_and_120_records`, `test_v2_targets_the_declaration_failure`, `test_v2_intents_and_tools_are_valid`, `test_v2_record_ids_unique` |
| v2 challenge immutability | `test_challenge_set_is_frozen_and_checksummed`, `test_challenge_families_appear_nowhere_in_training` |
| Leakage protection | `test_three_test_sets_are_disjoint`, `test_no_training_record_duplicates_a_challenge_record`, `test_no_v1_test_record_was_moved_into_training`, `test_external_benchmark_is_unchanged`, `test_no_semantic_family_spans_splits`, `test_original_internal_test_membership_is_preserved` |
| Declaration/logging contrasts | `test_v2_contains_declaration_logging_contrasts`, `test_v2_covers_prepare_versus_submit` |
| Function arguments | `test_v2_argument_records_validate_against_the_registry` |
| T4 requirement / P100 rejection | `test_notebook_requires_t4_and_rejects_p100`, `test_notebook_metadata_requests_t4` |
| LoRA language-layer targets | `test_notebook_targets_language_model_layers_only` |
| Zero-gradient abort | `test_notebook_aborts_on_zero_gradients` |
| Maximum 3 epochs | `test_notebook_uses_at_most_three_epochs` |
| Best-checkpoint restore | `test_notebook_restores_best_checkpoint` |
| Full acceptance gate | `test_gate_document_exists_and_is_pre_registered`, `test_full_gate_thresholds_are_as_registered`, `test_notebook_applies_frozen_gates` |
| Hybrid acceptance gate | `test_hybrid_gate_requires_per_intent_precision_and_recall`, `test_hybrid_rules_keep_declaration_hosted_below_080`, `test_notebook_keeps_declaration_hosted_below_080_recall` |
| Per-intent fast-path routing | `test_notebook_applies_frozen_gates` (`FAST_PATH_INTENTS` computed with P≥0.90 AND R≥0.90) |
| Hosted fallback | `test_router_still_disabled_until_a_gate_passes`, `test_hosted_remains_a_selectable_provider_mode` |
| Malformed adapter output | `test_router_malformed_output_falls_back_safely`, `test_router_validation_rejects_unknown_intent_and_tool` |
| Safety invariants | `test_v2_never_teaches_an_unsafe_target`, `test_v2_invariants_are_never_lowerable`, `test_mock_declaration_always_labelled`, `test_unknown_function_requests_select_no_tool`, `test_challenge_set_includes_unsafe_and_injection`, `test_router_never_claims_out_of_scope_responsibility` |
| Deterministic tool validation | `test_gate_requires_deterministic_tool_validation` |
| One-record caveat | `test_one_record_caveat_is_registered` |

## 4. Issues the tests caught during Step 4

1. **Two Step-3 tests encoded the pre-v2 dataset state** (`test_split_files_reconstruct_the_master`
   expected the split files to reconstruct the v1 master; `test_review_queue_prioritises_safety_and_ambiguity`
   expected queued records to still be `pending`). Both were updated to assert the *current*
   truth — the v2 splits reconstruct the v2 master **and** the archived v1 splits still
   reconstruct the archived v1 master; queued records are now `reviewed`. Step-3 *results*
   were not touched.
2. **Three new v2 records overlapped the immutable benchmark** (caught by
   `check_training_leakage` logic inside `validate_v2_dataset.py`): two ≈0.80 similar to
   `mfe-08`/`mfe-22`, one sharing a four-word run with `mfe-17`. Rewritten in the data.
3. **The router provider pointed at v1 outputs only.** After the v2 download it would have
   reported the stale v1 decision. Fixed to prefer `e2b_router_v2` and to read
   `gate_a`/`gate_b`; it now reports the v2 rejection with the exact failing criteria and
   would only ever report available on an explicit pre-registered gate pass.

## 5. Kaggle v2 run — verification trail

| Kernel version | Result | Cause / note |
|---|---|---|
| v1 | ERROR | dataset mounts at `/kaggle/input/datasets/<owner>/<slug>`; loader fixed to search recursively and print the mount |
| v2 | ERROR | `hashlib` used before import in the dataset cell |
| v3 | training + all 3 evaluations completed; crashed only in export (stale `GATE` name) | all numbers printed to the log |
| **v4** | **COMPLETE** | identical rerun (same data/config/seed, greedy decoding); artifacts downloaded and verified to match the v3 log — internal 0.8529, external 0.7812, challenge 0.7083, gates identical |

In-session guards that ran before training: T4/sm_75 check, challenge checksum
(`23327eae…`), worst train-vs-heldout similarity 0.809 and train-vs-challenge 0.820 (both
< 0.85), challenge families disjoint, non-zero smoke gradients [3.479, 1.292].

## 6. Reproduction

```bash
python scripts/validate_v2_dataset.py

cd backend
.venv/Scripts/python.exe -m pytest tests/test_step4_v2.py -q
.venv/Scripts/python.exe -m pytest -q --ignore=tests/test_hosted_integration.py
.venv/Scripts/python.exe -m pytest tests/test_hosted_integration.py -q   # needs GEMINI_API_KEY
```
