# AI Step 3 — Training Report

Branch: `ai-modeling` · Base model: `google/gemma-4-E2B-it` · Run: Kaggle kernel
`yuvineappadu/lamer-konekte-e2b-qlora-router` **version 15** · 2026-07-29

**Outcome: training ran and produced an adapter. The adapter FAILED the acceptance gate and
is NOT integrated. Hosted `gemma-4-26b-a4b-it` remains production.**

---

## 1. Result summary

| | Untuned E2B | **Tuned E2B** | Hosted 26B (Pipeline A) |
|---|---|---|---|
| Intent accuracy (internal, n=34) | 0.0% | **73.5%** | 70.6% |
| Tool accuracy | 20.6%* | **58.8%** | 50.0% |
| Structured-output validity | 0.0% | **100%** | 97.1% |
| Valid intent-enum rate | 0.0% | **100%** | 97.1% |
| Tool allow-list rate | 100% | **100%** | 100% |
| Unknown-function rate | 0% | **0%** | 0% |
| Safety pass rate | 100% | **100%** | 100% |
| Median latency | 484 ms | **4 438 ms** | 18 546 ms |
| **External benchmark (n=32)** | 0.0% | **75.0%** | — |

\* agreement-by-absence (expected `null`, predicted `None`), not real tool selection.

Improvement over untuned E2B: **+73.5 pp** intent, **+100 pp** structured validity.

## 2. Acceptance gate — REJECTED

| Criterion | Required | Actual | Result |
|---|---|---|---|
| Intent accuracy | ≥ 90% | 73.5% | **FAIL** |
| Tool accuracy | ≥ 90% | 58.8% | **FAIL** |
| Structured-output validity | 100% | 100% | PASS |
| Safety pass | 100% | 100% | PASS |
| Zero unknown-function execution | 0 | 0 | PASS |
| Improvement over untuned | ≥ 15 pp | +73.5 pp | PASS |
| English/mixed controls not regressed | — | not regressed | PASS |
| **ACCEPTED** | | | **false** |

The gate was **not** relaxed, no test record was moved, and nothing was re-run to chase a
better number. `FineTunedE2BRouterProvider.readiness()` reads these metrics directly and
reports:

```
available: false
reason: "adapter REJECTED by the Step-3 acceptance gate:
         intent_accuracy_ge_0.90, tool_accuracy_ge_0.90"
```

### A calibration problem worth the team's attention

The gate demands **≥90% intent accuracy**, but the production hosted 26B model achieves
only **70.6%** on this same split and prompt. The gate therefore sits above what production
itself delivers, which means an adapter that is genuinely better than production still
fails it.

That is a real observation, not an argument to lower the bar — the threshold was fixed in
advance and it stays fixed for this step. But **Step 4 should re-derive the threshold from
measured production performance** rather than from a round number.

## 3. Training configuration (as run)

| | |
|---|---|
| GPU | Tesla T4, 14.6 GiB, sm_75 |
| Quantisation | 4-bit NF4 + double quant |
| Compute dtype | fp16 (T4 has no usable bf16); AMP disabled, adapters in fp32 |
| LoRA | r=8, alpha=16, dropout=0.05 |
| Target modules | **205 language-model projections** (q/k/v/o/gate/up/down), addressed by full path |
| Trainable params | 12 079 104 / 3 948 099 104 (**0.31%**) |
| Sequence length | 384 (max observed 389, p95 376) |
| Batch | per-device 1 × grad-accum 8 = effective 8 |
| Epochs | 8, early stopping on eval loss (patience 2) |
| LR | 2e-4, cosine, warmup 3% |
| Gradient checkpointing | on, non-reentrant |
| Seed | 20260729 |
| **Training time** | **564 s (9.4 min)** |
| **Peak VRAM** | **9.21 GiB** |
| **Best eval loss** | **0.0893** (epoch 2) |

Loss curve: train 0.230 → 0.038; eval 0.121 → **0.089** → 0.091 → 0.098. Eval loss rises
after epoch 2, so early stopping selected the epoch-2 checkpoint. **170 training records is
too few for 8 epochs** — the model starts memorising.

## 4. Per-intent breakdown (tuned, internal test)

| Intent | F1 | Precision | Recall | Support |
|---|---|---|---|---|
| identify_catch | 0.923 | 1.000 | 0.857 | 7 |
| weather_query | 0.769 | 0.714 | 0.833 | 6 |
| log_catch | 0.700 | 0.583 | 0.875 | 8 |
| **make_declaration** | **0.625** | 1.000 | **0.455** | 11 |
| other | 0.667 | 0.500 | 1.000 | 2 |

### Likely failure categories

1. **`make_declaration` recall 0.455 is the single biggest loss.** Precision is 1.000, so
   when it says "declaration" it is always right — it simply misses more than half of them,
   and `log_catch` precision (0.583) suggests those misses land there. "Prepare my report"
   and "record my catch" are genuinely close in Morisyen, and the dataset has only 25
   declaration records.
2. **`other` precision 0.500** on 2 support records — too few to draw conclusions from,
   but it is the fallback class, so over-prediction there hides real intents.
3. **Tool accuracy (58.8%) lags intent accuracy (73.5%).** Getting the intent right but the
   tool wrong points at the argument/tool layer, which has the thinnest coverage
   (`queue_for_offline_sync` and `get_current_demo_date` have 2 records each).
4. **Uncertainty accuracy 66.7%** — the "ask instead of guessing" behaviour is the weakest
   of the safety-adjacent behaviours, though no unsafe output occurred.

## 5. What it took to get here — five real failures

Every failure was diagnosed from the actual kernel log and fixed at the cause. None was
worked around.

| Ver | Failure | Cause | Fix |
|---|---|---|---|
| v1 | `ValueError: model type gemma4 not recognized` | Kaggle's base `transformers` predates Gemma 4 | Dependency upgrade **before** any transformers import + explicit `CONFIG_MAPPING_NAMES` assertion → transformers 5.14.1 |
| v3 | Kernel **died**, `named symbol not found ... ops.cu` | Kaggle gave a **P100 (sm_60)**; bitsandbytes 4-bit needs sm_75+ and kills the process rather than raising | Detect compute capability; 4-bit only on sm_75+ |
| v5 | `CUDA error: no kernel image is available` | torch 2.10+cu128 ships **no sm_60 kernels at all**; `machine_shape: gpu-t4x2` was silently ignored | Correct accelerator enum is `NvidiaTeslaT4` |
| v8 | `OutOfMemoryError: tried to allocate 8.75 GiB` | `prepare_model_for_kbit_training` upcasts **every** non-4bit fp16 param to fp32; Gemma 4's embedding tables are huge | Replaced with a frugal prep: checkpointing + input grads + fp32 on **norms only** |
| v12 | **grad_norm = 0.0 at every step**, eval loss bit-identical across epochs | My own bug: a suffix match on `q_proj` hit the **vision/audio towers** (`Gemma4ClippableLinear`, `Gemma4VisionConfig \| Gemma4AudioConfig`), which a text-only task never runs — so the adapter sat outside the forward graph | Resolve targets **inside `model.language_model` only**, by full module path |

v13 then proved the diagnosis independently: with the artificial input-requires-grad hook
removed, the loss had **no `grad_fn` at all**. The notebook now carries a zero-gradient
guard that refuses to start full training if smoke-step grad norms are all zero — so this
class of silent no-op cannot recur unnoticed.

## 6. Decision

**Do not integrate.** Per the Step-3 rules for a failed gate:

- the adapter is **not** forced into the product;
- the training experiment is **retained** and fully reproducible;
- the actual result is documented above, unrounded;
- hosted `gemma-4-26b-a4b-it` **remains production**;
- likely failure categories are identified in §4.

`FineTunedE2BRouterProvider` ships **disabled**. It is not a selectable `provider_mode`, it
raises `RouterUnavailable` rather than falling back silently, and every route it would
produce is re-validated against the frozen intent and tool vocabularies.

## 7. Honest caveats

1. **34 internal test records.** One record is worth 2.9 pp. The 73.5% vs 70.6% gap over
   hosted 26B is **one record wide** and is *not* a reliable ranking.
2. **The untuned 0.0% floor flatters the improvement.** It is 0.0% largely because the
   compact prompt carries no output-format instruction, so +73.5 pp mostly measures
   "learned the output contract".
3. **The external benchmark result (75.0%) is the most trustworthy number here** — 32
   records the model never saw, checksum-verified unchanged, and never paraphrased into
   training.
4. **All 240 training records are AI-generated and unreviewed by a native Morisyen speaker.**
   The split reported as `reviewed_subset_accuracy` (0.500) reflects labels in the Kaggle
   dataset snapshot, not a real human review.
5. **Dataset snapshot drift:** the Kaggle dataset was uploaded before the provenance
   relabelling commit. Record text, splits, intents and tools are byte-identical (the
   kernel reports 240/170/36/34 and worst held-out similarity 0.769, matching the committed
   data); only `provenance` / `human_review_status` labels differ. Re-push before any
   further training run.
6. **Latency is not like-for-like** — 4 438 ms on a Kaggle T4 versus 18 546 ms for a hosted
   API call over the internet. A phone would be slower than the T4.

## 8. Artifacts

```
training/results/training_metrics.json      full run configuration + metrics
training/results/evaluation_metrics.json    untuned vs tuned + acceptance gate
training/results/training_history.csv       loss and grad-norm per step
training/results/e2b_comparison.csv         per-record untuned vs tuned
training/results/error_analysis.csv         every record the tuned model got wrong
training/results/E2B_ADAPTER_MODEL_CARD.md  model card
kaggle/outputs/e2b_router/                  adapter weights (gitignored, 17.7 MB)
```

## 9. Recommended next step

Close the `make_declaration` recall gap and the tool-selection gap before retraining:
more declaration records, more argument coverage for the thin tools, native-speaker review
of the queued 30, and a test split large enough that a single record is not worth 3 pp.
Then re-derive the acceptance threshold from measured production performance rather than a
round 90%.
