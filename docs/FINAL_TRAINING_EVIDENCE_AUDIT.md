# Final Training-Evidence Audit

Audited 2026-07-29T23:23:48.640837+00:00 · **36/36 claims supported by a stored artifact**

Every documented number is cross-checked against the artifact that produced it.
The audit fails if any claim lacks support, or if a forbidden claim appears.

| Claim | Documented | Artifact | Source | Supported |
|---|---|---|---|---|
| dataset records = 338 | `338` | `338` | master_records_v2.jsonl | YES |
| semantic families = 164 | `164` | `164` | master_records_v2.jsonl | YES |
| train = 248 | `248` | `248` | split field | YES |
| validation = 42 | `42` | `42` | split field | YES |
| internal test = 34 | `34` | `34` | internal_test_v1_34.jsonl | YES |
| external test = 32 | `32` | `32` | morisyen_cases.json | YES |
| challenge test = 24 | `24` | `24` | v2_challenge_test.jsonl | YES |
| external benchmark checksum matches manifest | `966c54640cde7d4d6a9052317b247e03ac59e803bb6ffdc38ccfd4cc9f820250` | `966c54640cde7d4d6a9052317b247e03ac59e803bb6ffdc38ccfd4cc9f820250` | external_test_manifest.json | YES |
| challenge set checksum matches manifest | `23327eae5f7e8ef00b2e6833f826acf27daca2e218c92e57aaf623e8fa00234f` | `23327eae5f7e8ef00b2e6833f826acf27daca2e218c92e57aaf623e8fa00234f` | v2_challenge_manifest.json | YES |
| Kaggle GPU = Tesla T4 | `Tesla T4` | `Tesla T4` | v2_training_metrics.json | YES |
| training duration ~552 s | `552` | `552` | v2_training_metrics.json | YES |
| peak VRAM = 9.21 GiB | `9.21` | `9.21` | v2_training_metrics.json | YES |
| best validation loss = 0.0577 | `0.0577` | `0.0577` | v2_training_metrics.json | YES |
| trainable parameters = 12,079,104 | `12079104` | `12079104` | v2_training_metrics.json | YES |
| adapter size ~48.4 MB (fp32 safetensors) | `48.4` | `48.4` | kaggle/outputs (gitignored) | YES |
| v1 internal intent = 73.5% | `0.7353` | `0.7353` | archive/v1/evaluation_metrics.json | YES |
| v1 external intent = 75.0% | `0.75` | `0.75` | archive/v1/evaluation_metrics.json | YES |
| v1 tool accuracy = 58.8% | `0.5882` | `0.5882` | archive/v1/evaluation_metrics.json | YES |
| v1 declaration recall = 0.455 | `0.4545` | `0.4545` | archive/v1/evaluation_metrics.json | YES |
| v2 internal intent = 85.3% | `0.8529` | `0.8529` | v2_evaluation_metrics.json | YES |
| v2 external intent = 78.1% | `0.7812` | `0.7812` | v2_evaluation_metrics.json | YES |
| v2 challenge intent = 70.8% | `0.7083` | `0.7083` | v2_evaluation_metrics.json | YES |
| v2 tool accuracy = 58.8% | `0.5882` | `0.5882` | v2_evaluation_metrics.json | YES |
| structured validity = 100% | `1.0` | `1.0` | v2_evaluation_metrics.json | YES |
| safety = 100% | `1.0` | `1.0` | v2_evaluation_metrics.json | YES |
| unknown-function rate = 0% | `0.0` | `0.0` | v2_evaluation_metrics.json | YES |
| routing latency ~4.6 s | `4600` | `4571` | v2_evaluation_metrics.json | YES |
| v2 internal declaration recall = 100% | `1.0` | `1.0` | v2_per_intent_metrics.csv | YES |
| v2 external declaration recall = 100% | `1.0` | `1.0` | v2_evaluation_metrics.json | YES |
| v2 challenge declaration recall = 72.7% | `0.7273` | `0.7273` | v2_evaluation_metrics.json | YES |
| gate A rejected | `False` | `False` | v2_evaluation_metrics.json | YES |
| gate B rejected | `False` | `False` | v2_evaluation_metrics.json | YES |
| decision = REJECTED | `REJECTED` | `REJECTED` | v2_evaluation_metrics.json | YES |
| gate doc pre-registered before training | `True` | `True` | V2_PRE_REGISTERED_ACCEPTANCE_GATE.md | YES |
| no forbidden claim in submission documents | `none` | `none` | docs/AI_SUBMISSION_SUMMARY.md, docs/AI_JUDGE_TECHNICAL_PROOF.md, docs/AI_DEMO_SCRIPT.md, docs/AI_LIMITATIONS.md, docs/AI_FINAL_HANDOFF.md, docs/AI_MODEL_SELECTION_DECISION.md, docs/AI_STEP4_FINAL_REPORT.md, kaggle/writeup.md | YES |
| approved rejection phrasing used | `training succeeded, but the adapter did not pass the production acceptance` | `['docs/AI_SUBMISSION_SUMMARY.md', 'kaggle/writeup.md']` | submission documents | YES |

## Approved phrasing

> "Training succeeded, but the adapter did not pass the production acceptance gate."

## Forbidden claims (verified absent)

adapter-as-production · universal 85.3% accuracy · all-Morisyen-native-verified ·
AI makes legal decisions · guaranteed marine safety · real ministry submission
