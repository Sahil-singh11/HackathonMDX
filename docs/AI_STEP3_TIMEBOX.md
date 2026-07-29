# AI Step 3 — Timebox

Assessed 2026-07-29 15:19 MUT. Deadline assumption inherited from `docs/TIMEBOX.md`
(2026-07-30 13:36 MUT); the team must correct it if the official deadline differs.

| Marker | Time (MUT) | From now |
|---|---|---|
| Now | 2026-07-29 15:19 | — |
| Major-feature freeze | 2026-07-30 10:36 | **~19.3 h** |
| Final submission verification | 2026-07-30 12:36 | ~21.3 h |
| Deadline (assumed) | 2026-07-30 13:36 | **~22.3 h** |

---

## Planned schedule

| Phase | Budget | Hard stop |
|---|---|---|
| Readiness + compact prompt freeze | 0.5 h | 15:50 |
| Dataset build (~240 records, families, splits) | 1.5 h | 17:20 |
| Validation scripts + all checks green | 1.0 h | 18:20 |
| Kaggle notebook + automation scripts | 1.5 h | 19:50 |
| Dataset push + notebook push + launch | 0.5 h | 20:20 |
| **Untuned E2B baseline (on Kaggle)** | 0.5 h | inside the run |
| Smoke test + full training | ≤ 4.0 h | **2026-07-30 01:00** |
| Download, evaluate, compare, integrate | 1.5 h | 02:30 |
| Reports, tests, commits | 1.5 h | 04:00 |
| Buffer before freeze | ~6 h | 10:36 |

---

## Stopping conditions

Training is **abandoned** (not retried) and hosted Gemma remains production if any of these
holds:

1. The memory smoke test cannot complete one forward + backward step after the documented
   OOM ladder has been exhausted.
2. Estimated full-training wall-clock exceeds **4 h**, or would finish after
   **2026-07-30 01:00 MUT**.
3. Kaggle GPU is unavailable or quota is exhausted, and no supported alternative runtime is
   reachable within the budget.
4. Leakage or semantic-family validation fails and cannot be fixed within 30 minutes.
5. The base model cannot be loaded as `google/gemma-4-E2B-it` — **no substitute model is
   ever used to keep the schedule**.

## Fallback procedure

1. Record the exact failure and its evidence in `docs/AI_STEP3_TRAINING_REPORT.md`.
2. Keep the dataset, notebook and automation committed and reproducible — they are
   deliverables in their own right.
3. Keep hosted `gemma-4-26b-a4b-it` as the production provider (it already passes every
   Step-1 gate and the Step-2 acceptance criteria).
4. Do **not** integrate `FineTunedE2BRouterProvider` as a default.
5. Do **not** claim training was launched or completed if it was not.
6. State the exact remaining human action, if any.

## Non-negotiables regardless of time pressure

- The 32-case external benchmark is never trained on and never paraphrased.
- Failed test examples are never moved into training after results are observed.
- The acceptance gate is never relaxed to make an adapter pass.
- No secret is printed, logged or committed.
