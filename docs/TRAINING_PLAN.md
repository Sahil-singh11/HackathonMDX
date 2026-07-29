# Training Plan — Lamer Konekte

Training must be attempted and evaluated without blocking the product.

## Status at baseline
**BLOCKED for launch**: Kaggle CLI not installed/authenticated on the dev machine. Everything below is prepared so a run starts within minutes of authentication. If auth never arrives, the blocker is reported honestly (brief §34 item 17).

## Baseline first (18A)
`evaluation/run_all.py --provider mock|hosted` measures: top-1 agreement, top-3 coverage, structured validity, correct uncertainty, false-confident errors, Morisyen intent, function selection, argument validity, hallucinated-rule rate, marine-safety refusal, latency, failure rate → `evaluation/results/baseline.{json,csv}` + `docs/BASELINE_REPORT.md`. Hosted baseline runs only after the API key exists; mock runs are labelled mock and never presented as model quality.

## Data (18B)
`training/scripts/build_training_data.py` renders supervised JSONL from evaluation cases + catalogue + safety templates → `training/data/{train,validation,test}.jsonl`. Split by observation/photographer; template de-dup across splits; leakage test in pytest. Card: `docs/TRAINING_DATASET_CARD.md`.

## Kaggle hardware gate (18C)
First notebook cell records GPU name, VRAM, BF16, CUDA, disk, and model access before any training.

- **Mode A — multimodal QLoRA** (E2B first, E4B only after memory test): batch 1, grad-accum, grad-checkpointing, 4-bit, LoRA r=8, short image res, warm-up run first. Targets: constrained candidates, structured output, uncertainty.
- **Mode B — text/structured QLoRA** (fallback when A doesn't fit): Morisyen intent, function selection, structured JSON, safe refusals. Doubles as future local intent router.
- **Mode C — calibration model** (only if A and B fail): transparent classifier over Gemma confidence + image quality + candidate rank. Gemma stays central.

## Acceptance (18E)
Integrate only if: loads reliably; held-out eval done; structured validity, unsafe rate, false confidence not worse; ≥1 target metric improves; latency acceptable; licence permits. Otherwise: production stays on hosted Gemma, experiment preserved, honest report in `docs/MODEL_TRAINING_REPORT.md`.

## Automation
`kaggle/notebooks/{train_gemma4_qlora,train_gemma4_text_adapter,evaluate_adapter,audio_gate}.ipynb`; push/monitor/download scripts in `scripts/` (bash + ps1). Credentials never echoed.
