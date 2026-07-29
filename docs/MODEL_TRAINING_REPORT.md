# Model Training Report — honest status

**Outcome at reporting time: NOT LAUNCHED (blocked), no training success is claimed.**

## What exists and works
- Supervised dataset: 72 records (53 train / 11 validation / 8 test) across image-identification, text-intent+function, and safety-refusal types, with observation-level and template-family leakage controls (`training/data/`, card in `docs/TRAINING_DATASET_CARD.md`).
- Kaggle notebooks: `train_gemma4_qlora.ipynb` (Mode A, E2B 4-bit LoRA r=8, batch 1 + grad-accum 8 + checkpointing, hardware gate first, warm-up before full run), `train_gemma4_text_adapter.ipynb` (Mode B), `evaluate_adapter.ipynb` (held-out §18E acceptance).
- Automation: `scripts/kaggle_push_training.sh` (private dataset + GPU kernel push), monitor + download scripts.

## Blockers (in order encountered)
1. Kaggle CLI not installed/authenticated on the build machine → cannot create datasets or start GPU kernels.
2. HF token + Gemma licence acceptance needed inside the training notebook (Kaggle Secret `HF_TOKEN`).

## Acceptance rule (unchanged)
The adapter integrates only if it loads reliably, held-out evaluation completes, structured validity / unsafe rate / false confidence are not worse, ≥1 target metric improves, latency is acceptable and licensing permits. Otherwise production stays on hosted Gemma and the experiment is preserved and reported as-is.

## Mode C fallback
If both adapter modes fail on Kaggle, the calibration-model fallback (Gemma confidence + image quality + candidate rank) is specified in `docs/TRAINING_PLAN.md`; not started.

`training/results/` holds the honest placeholders (`metrics.json` with `"status": "blocked"`); they are overwritten by real numbers when a run completes.
