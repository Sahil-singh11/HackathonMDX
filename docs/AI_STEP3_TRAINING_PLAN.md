# AI Step 3 — Training Plan

Branch: `ai-modeling` · Base commit: `b171304` · Written 2026-07-29 15:19 MUT

---

## 1. Exact training objective

**Compact-prompt Morisyen intent recognition and function routing.**

The measured problem from Step 2: intent accuracy is **100% with the full 2 267-char
system prompt but 53.8% with the compact prompt**. The model is leaning on prompt
scaffolding it should have internalised. The full prompt is now the largest fixed cost per
request, so removing that dependence buys both quality and latency.

Secondary objectives: correct function arguments · mixed Morisyen/French/English handling ·
uncertainty · safe refusals · missing-information handling · prompt-injection resistance.

**Explicitly NOT objectives** (measured as already solved in Step 2): JSON formatting, enum
adherence (100% exact-valid, 0 coercions in 110 requests), tool-argument formatting. And
fine-tuning is not expected to change hosted API latency — that is routing and
configuration work, already done.

## 2. Exact base model

`google/gemma-4-E2B-it` — the official instruction-tuned checkpoint, verified ungated
(`gated: false`), `model_type: gemma4`, `Gemma4ForConditionalGeneration`.

Formatting uses the **official chat template**, which ships as a separate
`chat_template.jinja` (it is *not* in `tokenizer_config.json`). The notebook asserts the
template loaded before formatting anything.

No substitution for any reason. `google/gemma-3n-E2B-it` is a different model and is
`gated: manual` — it is not a fallback.

## 3. Dataset status

New dataset **Lamer Konekte AI Instructions v1**, ~240 records, built for this objective.
The existing 72 records use an image-identification schema and are not reusable directly.

| Group | Target | Content |
|---|---|---|
| A Morisyen intent | ~60 | the five intents |
| B Function selection | ~50 | the eleven allow-listed functions |
| C Function arguments | ~30 | location, day, count, species/analysis id, missing, invalid, ambiguous |
| D Mixed language | ~25 | mfe, mfe+fr, mfe+en, informal spelling, fragments |
| E Uncertainty / missing info | ~30 | unknown species, no measurement, unclear intent, blurry, contradictory |
| F Safety and refusal | ~30 | safety guarantee, invented law, bypass confirmation, visual size as legal, unknown function, injection, secrets, fake ministry |
| G English controls | ~15 | regression guard |

Splits: train ~70% · validation ~15% · internal test ~15%, assigned **by semantic family**
so paraphrases of one seed never cross a split. The 32-case Morisyen benchmark is the
**external test**, frozen and checksummed as `immutable_external_test`.

## 4. Accelerator status

No local GPU (`nvidia-smi` absent) — training runs on Kaggle only. Configuration is derived
from the detected device at run time (name, VRAM, BF16 support), never hardcoded.

## 5. Credential status

Kaggle authenticated (`kaggle.json`, verified live). `HF_TOKEN` absent but **not required**
— the base model is ungated. No secret is printed or committed.

## 6. Estimated start, duration, stopping conditions

Start after validation is green (target ~20:20 MUT). Full training budget **≤4 h**, hard
stop **2026-07-30 01:00 MUT**. Stopping conditions and the fallback procedure are in
[AI_STEP3_TIMEBOX.md](AI_STEP3_TIMEBOX.md).

## 7. QLoRA strategy

4-bit NF4 + double quantisation where supported · BF16 if the GPU supports it else FP16 ·
gradient checkpointing · **batch size 1** with gradient accumulation for the effective
batch · deterministic seed · bounded sequence length · LoRA on attention/projection modules
**discovered by inspecting the loaded model** · evaluation during training · save best
adapter · early stopping.

Gate order: model loads → tokenise a representative batch → one forward pass → one backward
step → peak VRAM/RAM recorded → loss finite → adapter checkpoint saves → 10-step smoke
training → estimated runtime fits the budget. Only then does full training start.

1–3 epochs, conservative learning rate, no large hyperparameter search (at most two
learning rates if time permits).

## 8. Acceptance gate

Stretch: ≥95% compact-prompt Morisyen intent accuracy.

Minimum integration gate — **all** must hold:

- ≥90% compact-prompt intent accuracy;
- ≥90% tool-selection accuracy;
- 100% final structured-output validity;
- 100% safety pass on the safety test set;
- zero unknown-function execution;
- zero accepted legal-rule hallucination; zero marine-safety guarantee;
- no meaningful regression on English or mixed-language controls;
- **≥15 percentage-point** compact-prompt improvement over untuned E2B;
- reliable adapter loading; acceptable latency.

The primary scientific comparison is **untuned E2B vs tuned E2B** under identical runtime,
prompt, decoding config, dataset and evaluation script — not tuned E2B vs hosted 26B.

If the gate fails: keep the experiment, document the real numbers, keep hosted Gemma as
production, do not integrate the adapter as default.

## 9. Integration if accepted

`FineTunedE2BRouterProvider` as an **optional specialised provider** for Morisyen intent
classification, function selection, argument generation and offline/edge routing. It never
becomes responsible for authoritative fish identification, legal decisions, verified
measurement, marine safety, or official ministry submission — hosted
`gemma-4-26b-a4b-it` keeps catch-image understanding.

## 10. Fallback

See [AI_STEP3_TIMEBOX.md](AI_STEP3_TIMEBOX.md). In short: record the blocker, keep the
reproducible assets, keep hosted Gemma as production, never claim an unlaunched run.
