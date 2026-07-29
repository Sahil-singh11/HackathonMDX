# Untuned `google/gemma-4-E2B-it` Baseline

Measured on Kaggle, kernel version 8, 2026-07-29. Real inference on a real GPU.
This is the "before" half of the primary Step-3 comparison: **untuned E2B vs tuned E2B**
under identical runtime, prompt, decoding configuration, dataset and evaluation code.

---

## 1. Runtime

| | |
|---|---|
| Model | `google/gemma-4-E2B-it` (official, ungated) |
| Parameters | 3.94 B |
| GPU | Tesla T4, 14.6 GiB, compute capability **7.5** |
| Quantisation | 4-bit NF4 + double quant (bitsandbytes usable at sm_75) |
| Compute dtype | `torch.float16` (T4 has no usable bf16) |
| transformers | 5.14.1 (`gemma4` architecture registered) |
| Chat template | official `chat_template.jinja`, 18 567 chars |
| Prompt | `compact_router_v1`, SHA-256 `44299533f59cc907…`, 1 019 chars |
| Decoding | greedy, `max_new_tokens=96`, no sampling |
| Max sequence length | 384 (max observed 389, p95 376, mean 363) |

## 2. Results — internal held-out test (n = 34)

| Metric | Value |
|---|---|
| **Intent accuracy** | **0.0%** |
| Tool-selection accuracy | 20.6% |
| **Structured-output validity** | **0.0%** |
| Valid intent-enum rate | 0.0% |
| Tool allow-list rate | 100% |
| Unknown-function rate | 0% |
| Safety pass rate | 100% |
| Uncertainty accuracy | 0.0% |
| Median latency | 472 ms |

## 3. Results — immutable external benchmark (n = 32)

| Metric | Value |
|---|---|
| Intent accuracy | **0.0%** |

Checksum verified against `external_test_manifest.json` before scoring; the benchmark was
not modified.

## 4. What these numbers actually mean

**The untuned model never produced parseable structured output.** `structured_validity` is
0.0, so `intent_accuracy` is 0.0 by construction — there was nothing to read an intent
from. This is a floor, not a subtle deficiency.

**This is partly an artefact of the compact prompt, and that must be stated plainly.**
`compact_router_v1` deliberately contains no worked examples and no JSON key list, because
its purpose is to test whether the model can route *without* prompt scaffolding. An
instruction-tuned model that has never seen this task therefore has no reason to emit JSON
at all. So the 0.0% measures two things at once:

1. it has not learned the output contract, and
2. we cannot observe whether it understood the Morisyen intent.

The tuned model will learn both from the same training data, so a large improvement is
expected and is **not by itself evidence of better Morisyen understanding**. The honest
reading of any improvement is "the adapter learned the routing contract", with intent
quality only demonstrable on the subset where output is parseable.

**Two results are genuinely informative even at the floor:**

- **Tool allow-list rate 100% and unknown-function rate 0%.** Even producing unusable
  prose, the untuned model never named a function outside the offered list. The allow-list
  is not the thing training needs to fix.
- **Safety pass rate 100%.** No safety-category record produced an out-of-allow-list call.

**Tool accuracy 20.6% with 0% structured validity** is not a contradiction: `tool_ok` counts
cases where the expected tool was `null` and the parser also returned `None`. It is
measuring agreement-by-absence, not tool selection. It should be read as ~0% real
tool-selection capability.

## 5. Why the fairer product comparison is against hosted 26B

Because the untuned E2B floor is so low, comparing the tuned adapter only against it would
flatter the result. The product-relevant question is measured separately in
`evaluation/results/system_pipeline_comparison.json`: hosted `gemma-4-26b-a4b-it` routing
the *same* test split with the *same* frozen compact prompt (plus a short format hint,
which the E2B baseline did not receive — noted so the two are not confused).

Step 2 measured the hosted model at 100% intent accuracy with the full production prompt
and 53.8% with the compact prompt. That 53.8% is the number the adapter has to beat to be
worth putting in the product.

## 6. Artifacts

- `evaluation/results/e2b_untuned_baseline.json` — the summary above, machine readable
- `evaluation/results/e2b_untuned_baseline.csv` — per-record predictions
- Kaggle kernel: `yuvineappadu/lamer-konekte-e2b-qlora-router`, version 8

## 7. Caveat on this run

Kernel version 8 completed the untuned baseline and then failed during LoRA preparation
with a CUDA OOM (`prepare_model_for_kbit_training` upcasting embeddings fp16→fp32 needed
8.75 GiB on a 14.6 GiB card). The baseline numbers above were produced *before* that
failure and are unaffected by it. See `docs/AI_STEP3_TRAINING_REPORT.md`.
