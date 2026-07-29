# AI Technical Proof — for Judges

Team Ctrl200 · Lamer Konekte · 2026-07-30
Every number below is reproducible from committed artifacts; file paths are given inline.
Nothing here describes the fine-tuned adapter as production — it is an evaluated
experiment that **did not pass** its pre-registered acceptance gate.

---

## 1. Models — exact identifiers

| Role | Model | Access |
|---|---|---|
| **Production** (Morisyen/English understanding, function selection, structured responses, catch-image analysis) | `gemma-4-26b-a4b-it` | hosted, official `google-genai` SDK 2.14.0 |
| **Fine-tuning base** (experiment only) | `google/gemma-4-E2B-it` (3.94 B, official instruction-tuned checkpoint, ungated) | Hugging Face |
| Accelerator | **Kaggle Tesla T4** (sm_75), explicitly requested via `machine_shape: NvidiaTeslaT4` | Kaggle |

The notebook *refuses* to run below sm_75: a P100 was measured to crash outright
(torch 2.10+cu128 ships no sm_60 kernels; bitsandbytes 4-bit kills the process).

## 2. Method — QLoRA, corrected for Gemma 4's architecture

4-bit NF4 + double quantisation, fp16 compute, LoRA r=8 α=16 on **205 language-model
projection layers addressed by full module path** — Gemma 4 wraps projections in
`Gemma4ClippableLinear` and its vision/audio towers reuse the same leaf names, so naïve
suffix matching silently attaches adapters outside the text forward path (measured:
grad_norm 0.0 at every step). The notebook verifies **non-zero smoke gradients**
([3.479, 1.292]) and aborts otherwise. Trainable: **12 079 104 / 3.95 B (0.31%)**.

| Training fact | Value |
|---|---|
| Duration | **9.2 min** (552 s) |
| Peak VRAM | **9.21 GiB** / 14.6 |
| Epochs | ≤3, early stopping patience 1, best checkpoint restored |
| Validation loss | 0.0878 → 0.0663 → **0.0577** (best epoch 3) |
| Adapter size | **48.4 MB** fp32 safetensors (12.08 M params); reload verified deterministic |
| Reproducibility | seed 20260729, greedy decoding — kernel v3 and v4 produced identical metrics |

Kernel: `yuvineappadu/lamer-konekte-e2b-qlora-router-v2` (v4 = COMPLETE).

## 3. Dataset — Lamer Konekte AI Instructions v2

| | |
|---|---|
| Records | **338** across **164 semantic families** (train 248 / validation 42) |
| Built from | 240 reviewed v1 records + **98 targeted** at measured v1 failures |
| Splitting | **by semantic family** — paraphrases of one seed can never straddle a split; verified zero straddling |
| Provenance honesty | 30 records approved as written by the project owner (**not** native-speaker verified); 308 remain `AI_generated_review_required` |

**Three test sets, never merged into one headline number:**

| Set | n | Protection |
|---|---|---|
| Original internal test | 34 | v1 membership pinned (`internal_test_v1_34.jsonl`), verified 34/34 intact |
| **Immutable external benchmark** | 32 | never trained on, never paraphrased; SHA-256 manifest; leakage checker rejects even a shared **four-word run** |
| Frozen v2 challenge | 24 | committed **before** training; families appear nowhere in training |

**Leakage status: ALL PASS** (`scripts/validate_v2_dataset.py`; reports in
`training/results/v2_*.json`). The checker caught 11 real overlaps across v1+v2 authoring
(e.g. shared runs like *"met sa dan mo"*); all were fixed **in the data**, never by
relaxing a threshold. The training notebook re-runs leakage guards in-session (worst
train-vs-heldout similarity 0.809; train-vs-challenge 0.820; both < 0.85).

## 4. Results — identical scoring code across all systems

### Internal test (34; one record ≈ 2.9 pp)

| | Untuned E2B | v1 tuned | **v2 tuned** | Hosted 26B (production) |
|---|---|---|---|---|
| Intent accuracy | 0.0%* | 73.5% | **85.3%** | 70.6% |
| Tool accuracy | 20.6%† | 58.8% | 58.8% | 50.0% |
| Structured validity | 0.0% | 100% | **100%** | 97.1% |
| Safety pass | 100% | 100% | **100%** | 100% |
| Median latency | 446 ms | 4 438 ms | **4 571 ms** | 18 546 ms |

\* the compact prompt carries no format instruction — the untuned floor measures "hasn't
learned the output contract", stated honestly rather than used to flatter the improvement.
† agreement-by-absence, not real selection.

### External benchmark (32): 0.0% → 75.0% (v1) → **78.1%** (v2)
### Challenge set (24): intent **70.8%**, tool 62.5%, mixed-language 100%, safety 100%

### The targeted improvement — the headline of the modelling work

v1's dominant failure was `make_declaration` recall **0.455** (6 of 11 missed, 4 leaking
into `log_catch`). v2 added 54 declaration-focused records plus explicit
declaration-vs-logging contrast families. Result:

| make_declaration | v1 | **v2** |
|---|---|---|
| Internal recall | 0.455 | **1.000** (11/11, zero over-predictions) |
| External recall | — | **1.000** (3/3) |
| Challenge recall (unseen families) | — | 0.727 |

### Safety, across every evaluated system and set

100% safety pass · **0** unknown-function executions · **0** accepted legal hallucinations ·
**0** marine-safety guarantees. Independently enforced server-side by an explicit tool
allow-list (12 functions), Pydantic argument validation, mandatory species confirmation,
and a deterministic rules engine — the model is never trusted to self-validate.

## 5. Pre-registered gates and the rejection

Gates were **committed before training** (`docs/V2_PRE_REGISTERED_ACCEPTANCE_GATE.md`),
derived from measured production performance, and applied verbatim:

| Gate | Result | Failing criteria |
|---|---|---|
| A — full default router | **FAILED** | external intent 78.1% < 80% (0.6 records); tool 58.8% < 80%; min critical recall 66.7% < 75% |
| B — hybrid fast path | **FAILED** | tool 58.8% < 70% (sole failure; `make_declaration` individually qualified at P/R 1.000/1.000) |

**Decision: REJECTED.** Training succeeded, but the adapter did not pass the production
acceptance gate. No threshold was altered after seeing results; no test example was moved.
`FineTunedE2BRouterProvider` ships disabled, reports the exact failing metrics, raises
rather than silently activating, and is not a selectable provider mode. Hosted
`gemma-4-26b-a4b-it` remains production.

## 6. Verification trail

- 306 offline + 8 live hosted tests pass (`pytest`; live tier marked `live`, real API calls)
- Release gate: **ALL CHECKS PASSED** (`scripts/release_gate.sh`)
- v1 snapshot frozen with SHA-256 manifest (`training/archive/v1/`); Step-3 rejection preserved verbatim
- Full run/failure history — including every Kaggle kernel failure and its diagnosis — in
  `docs/AI_STEP3_TRAINING_REPORT.md` and `docs/AI_STEP4_FINAL_REPORT.md`
