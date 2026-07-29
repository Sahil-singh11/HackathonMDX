# AI Step 4 — Final Report

Branch: `ai-modeling` · Started from commit `2715a34` · 2026-07-29/30 MUT
Run: Kaggle kernel `yuvineappadu/lamer-konekte-e2b-qlora-router-v2`
(training + full evaluation first completed in kernel **v3**, which crashed only in the
final export cell on a stale variable name; kernel **v4** is the identical rerun — same
data, same config, same seed 20260729, greedy decoding — that reached COMPLETE with
artifacts).

**Outcome: v2 training ran and produced a materially better adapter — the targeted
`make_declaration` fix worked completely (recall 0.455 → 1.000) — but the adapter FAILED
both pre-registered gates on tool accuracy, so the decision is REJECTED. Hosted
`gemma-4-26b-a4b-it` remains the production router. No gate threshold was touched.**

---

## 1. Fair comparison — identical scoring code, three separate test sets

### Original internal test (34 records — one record ≈ 2.9 pp)

| | Untuned E2B | v1 tuned | **v2 tuned** | Hosted 26B |
|---|---|---|---|---|
| Intent accuracy | 0.0% | 73.5% | **85.3%** | 70.6% |
| Tool accuracy | 20.6%* | 58.8% | **58.8%** | 50.0% |
| Structured validity | 0.0% | 100% | **100%** | 97.1% |
| Valid intent-enum rate | 0.0% | 100% | **100%** | 97.1% |
| Unknown-function rate | 0% | 0% | **0%** | 0% |
| Safety pass | 100% | 100% | **100%** | 100% |
| Median latency | 446 ms | 4 438 ms | **4 571 ms** | 18 546 ms |

\* agreement-by-absence (expected `null`, predicted `None`), not real selection.

### Immutable external benchmark (32 records)

| | Untuned | v1 tuned | **v2 tuned** |
|---|---|---|---|
| Intent accuracy | 0.0% | 75.0% | **78.1%** |

### Frozen v2 challenge test (24 records, families nowhere in training)

| Metric | v2 tuned |
|---|---|
| Intent accuracy | **70.8%** |
| Tool accuracy | **62.5%** |
| Structured validity | 100% |
| Safety pass | 100% |
| Mixed-language accuracy | 100% |
| Median latency | 4 508 ms |

The three sets are reported separately and are **not** merged into one headline number.

## 2. Per-intent results (internal test, v2 tuned)

| Intent | Precision | Recall | F1 | Support | v1 recall |
|---|---|---|---|---|---|
| identify_catch | 1.000 | 0.714 | 0.833 | 7 | 0.857 |
| weather_query | 0.667 | 0.667 | 0.667 | 6 | 0.833 |
| log_catch | 0.875 | 0.875 | 0.875 | 8 | 0.875 |
| **make_declaration** | **1.000** | **1.000** | **1.000** | **11** | **0.455** |
| other | 0.500 | 1.000 | 0.667 | 2 | 1.000 |

Confusion matrix (expected → predicted):

| | identify | weather | log | declaration | other |
|---|---|---|---|---|---|
| identify_catch (7) | **5** | 1 | 1 | 0 | 0 |
| weather_query (6) | 0 | **4** | 0 | 0 | 2 |
| log_catch (8) | 0 | 1 | **7** | 0 | 0 |
| make_declaration (11) | 0 | 0 | 0 | **11** | 0 |
| other (2) | 0 | 0 | 0 | 0 | **2** |

**The targeted fix landed exactly where aimed:** every one of the 11 internal declarations
is now correct, with zero over-prediction; the 4-records-into-`log_catch` leak from v1 is
gone, and the external set's 3 declarations are also all correct. The honest caveat comes
from the frozen challenge set (families never seen in training): declaration recall there
is **0.727** (8 of 11) with precision 0.889 — strong, but the internal 1.000 partly
reflects stylistic proximity to the training families.

**The regression moved elsewhere:** `identify_catch` recall dropped 0.857 → 0.714 (one
record) and `weather_query` 0.833 → 0.667 (one record, now leaking to `other`). At 2.9 pp
per record these single-record moves are noise-level individually, but they are why gate
A10 (min critical recall ≥ 0.75) failed at 0.667.

## 3. The frozen gates, applied exactly as pre-registered

### Gate A — full default router: **FAILED (3 of 13)**

| Criterion | Threshold | Actual | Result |
|---|---|---|---|
| A1 internal intent | ≥ 85% | 85.3% | PASS |
| **A2 external intent** | ≥ 80% | **78.1%** | **FAIL** (by 0.6 records) |
| **A3 tool accuracy** | ≥ 80% | **58.8%** | **FAIL** |
| A4 structured validity | 100% | 100% | PASS |
| A5 safety | 100% | 100% | PASS |
| A6 unknown-function | 0% | 0% | PASS |
| A7 legal hallucination | 0% | 0% | PASS |
| A8 marine guarantee | 0% | 0% | PASS |
| A9 declaration recall | ≥ 80% | **100%** | PASS |
| **A10 min critical recall** | ≥ 75% | **66.7%** (weather_query) | **FAIL** |
| A11 English regression | none | none | PASS |
| A12 median latency | ≤ 7 000 ms | 4 571 ms | PASS |
| A13 adapter save/reload | reliable | deterministic ✔ | PASS |

### Gate B — hybrid fast path: **FAILED (1 of 9 core criteria)**

| Criterion | Threshold | Actual | Result |
|---|---|---|---|
| B1 internal intent | ≥ 78% | 85.3% | PASS |
| B2 external intent | ≥ 78% | 78.1% | PASS |
| **B3 tool accuracy** | ≥ 70% | **58.8%** | **FAIL** |
| B4–B9 | — | all pass | PASS |
| B10/B11 qualifying intents (P ≥ 90% and R ≥ 90%) | — | **`make_declaration` only** (1.000/1.000) | qualifies |

Gate B fell on a single criterion: **tool accuracy 58.8% vs the required 70%**. One intent
(`make_declaration`) individually qualified for a fast path, but the gate's overall tool
bar exists precisely because a router that picks the right intent and the wrong function
still executes the wrong thing.

### Decision: **C — REJECTED**

Per the pre-registered contract: `FineTunedE2BRouterProvider` stays **disabled**, hosted
`gemma-4-26b-a4b-it` remains the production router, and the thresholds were not revisited
after seeing the numbers.

## 4. Training run facts

| | v2 (kernel v3/v4) |
|---|---|
| GPU | Tesla T4, sm_75 (accelerator check enforced in-notebook) |
| Quantisation | 4-bit NF4 + double quant, fp16 compute, fp32-norm prep |
| LoRA | r=8, α=16, **205 language-model projections** (towers excluded) |
| Trainable | 12 079 104 / 3.95 B (0.31%) |
| Epochs | ≤ 3, early stopping patience 1, best checkpoint restored |
| Smoke gradients | non-zero verified: [3.479, 1.292] |
| Estimated runtime | 18.2 min · actual **9.2 min** |
| Eval loss by epoch | 0.0878 → 0.0663 → **0.0577** (best = epoch 3; still improving at the 3-epoch cap) |
| Peak VRAM | **9.21 GiB** |
| Adapter reload | files ✔ config ✔ deterministic ✔ |
| Dataset | v2: 248 train / 42 val; challenge checksum verified in-session (`23327eae…`); worst train-vs-heldout similarity 0.809, train-vs-challenge 0.820, all < 0.85 |

Launch-failure honesty: kernel v1 failed because Kaggle mounts datasets at
`/kaggle/input/datasets/<owner>/<slug>` (loader made recursive + self-diagnosing);
kernel v2 failed on a missing `hashlib` import; kernel v3 completed training and all
evaluation but crashed in the export cell on a leftover `GATE` name; kernel v4 is the
clean, artifact-complete rerun. Every failure was diagnosed from the real log.

## 5. What Step 4 proved and what it didn't

**Proved:**
- Targeted data works. 54 new declaration-focused records took `make_declaration` from
  the worst intent (F1 0.625) to perfect (F1 1.000) without inflating false positives.
- The compact-prompt objective is now within reach: internal intent 85.3% vs the hosted
  production model's 70.6% on the identical split and prompt — with a 4.2× latency
  advantage and zero hosted calls.
- External generalisation improved (75.0% → 78.1%) — it just missed the 80% bar, by less
  than one record-equivalent (0.6 of 32). On the external set `make_declaration` was also
  perfect (1.000/1.000 on its 3 cases).
- Safety held everywhere: 100% pass, 0 unknown-function, 0 legal hallucination, 0 marine
  guarantee, across all three test sets in both v1 and v2.

**Not fixed:**
- **Tool accuracy did not move: 58.8% → 58.8% (internal).** The 24 added argument records
  improved the challenge-set tool number (62.5%) but not the internal one. Intent and tool
  selection are evidently not learning from the same signal at this dataset size; the
  tool head needs either many more examples per tool or a different target format
  (e.g.训 the tool decision as a separate, shorter output).
- Small-set volatility: single records moved `identify_catch` and `weather_query` recall
  below the A10 bar. A 34-record test cannot certify per-intent floors; the gate design
  itself now needs a bigger internal set before a v3 attempt.
- Eval loss was still falling at the 3-epoch cap (0.0577 at epoch 3), so the conservative
  cap — chosen because v1 overfit after epoch 2 — may have left a little accuracy on the
  table this time. A v3 run can safely try 4 epochs with the same early stopping.

## 6. Artifacts

```
training/results/v2_*.json / *.csv       metrics, per-intent, confusion, arguments
training/archive/v1/                     untouched v1 baseline for comparison
kaggle/outputs/e2b_router_v2/            adapter weights (gitignored)
docs/V2_PRE_REGISTERED_ACCEPTANCE_GATE.md   the contract, committed before training
docs/V1_TARGETED_ERROR_ANALYSIS.md       why v2 targeted what it did
docs/TRAINING_DATASET_V2_CARD.md         dataset provenance and limits
```

## 7. Recommended next step (post-hackathon)

1. **Fix the tool head, not the intent head.** Intent is near-solved (85.3%); tool
   selection is flat at 58.8%. Try a two-stage target (intent first, then tool given
   intent) or oversample tool-discriminative pairs.
2. **Grow the internal test to ≥ 100 records** before running any gate with per-intent
   floors — at 34 records the floors are decided by single records.
3. Native-speaker review of the 308 unreviewed records remains the largest data risk.
4. External accuracy (78.1%) missed the bar by 0.6 records; with the tool head fixed and
   a modest data pass, both failed criteria are plausibly reachable in one more run.
