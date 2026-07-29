# Training Scope Decision

Updated: AI Step 2 · Branch `ai-modeling` · Model `gemma-4-26b-a4b-it`
**No training was run in this step.** This document sets the scope for when it is.

Evidence: `evaluation/results/structured_output_experiments.json` (110 requests across 5
runnable configurations), `evaluation/results/latency_stages.json`,
`docs/AI_PRODUCTION_CONFIG_DECISION.md`.

---

## 1. The decision rule and which branch applies

The Step-1 plan said: *if native structured output reaches ≥95% exact enum validity,
drop schema formatting as the primary fine-tuning objective.*

**Measured exact enum validity in the selected production configuration: 100%
(22/22). Enum coercion fired 0 times across all 110 requests, in every configuration.**

→ **Schema formatting is REMOVED as a fine-tuning objective.**

This reverses the Step-1 recommendation, and the reversal is deliberate. Step 1 reported
invalid enums (`intent: "species_identification"`, `confidence_label: "none"`, prose in
`recommended_next_step`) and concluded schema adherence was the top gap. Step 2 measured
it properly and found the opposite: with the current prompt the model's enum adherence is
perfect, and the high-looking `coercion_rate` was an artifact of a transport-model length
bound invented in Step 2, not an enum failure. See
[AI_PRODUCTION_CONFIG_DECISION.md §4](AI_PRODUCTION_CONFIG_DECISION.md).

Note the nuance: it is *prompt-instructed* JSON that achieves 100%. The **native**
`response_json_schema` path reached only 59.1% exact enum validity — but that is a
decoding-path defect (the model degenerates to the output ceiling), not something
fine-tuning the response format would fix, and that path is not in production.

---

## 2. Training objectives — IN scope

Ranked by measured gap.

1. **Morisyen intent quality and phrasing.** Intent accuracy was 100% with the full
   prompt, but collapsed to **53.8%** the moment the prompt was compacted (config E) —
   the model is leaning on lengthy prompt guidance rather than internalised understanding.
   A adapter that holds intent accuracy with a small prompt is the single highest-value
   objective: it buys both quality *and* latency headroom.
2. **Constrained candidate selection.** Selecting only from the supplied shortlist and
   returning `null` when evidence is thin is currently enforced server-side by the
   allow-list, not by the model. Training this in reduces reliance on the boundary.
3. **Uncertainty calibration.** `confidence_label` is produced, but nothing yet validates
   that "high" is actually more reliable than "low". Needs a labelled set before it can be
   a training target.
4. **Function-call selection.** Correct in every live test so far, including the lean
   turn-1 prompt, but only a handful of routes have been exercised. Worth training only
   after a larger evaluation set exists — currently there is no measured deficit.
5. **Safe refusals.** 100% safety pass across 110 requests, including both injection
   cases. Maintain by regression testing, not by training.

## 3. Training objectives — OUT of scope

- **Enum adherence** — already 100%.
- **Structured JSON consistency** — raw JSON parse rate already 100% in production.
- **Tool-argument formatting** — no malformed-argument failure observed; `record_catch`
  and `get_marine_conditions` arguments validated cleanly in every live run.

If a future evaluation shows exact enum validity dropping below 95%, these return to
scope. The metric to watch is `enum_coercion_rate_pct`, not `coercion_rate_pct`.

---

## 4. Latency is explicitly NOT a training problem

Median end-to-end latency fell from ≈33 s (Step 1) to **10.1 s** with **no model change**
— purely routing, prompt placement and thinking configuration. Fine-tuning will not
change hosted API latency. Latency stays owned by:

| Lever | Status |
|---|---|
| Routing (two-turn split, lean turn-1 prompt) | Done — turn 1 cut from 10–19 s to 3.9–5.2 s |
| Thinking configuration | Done — `MINIMAL` on tool selection; default elsewhere (measured faster) |
| Prompt size | Compact prompt built and measured; **not adopted** (costs intent accuracy) — this is what objective 1 above would unlock |
| Output size | No cap possible: caps consume hidden thinking tokens and return empty text |
| Image size | Measured; 1280 retained (768 was slower, 1024-vs-1280 inconclusive on current fixtures) |
| Caching | Marine forecast cache + demo-location pre-warm already in place; never cache private user content, never present a cached result as new inference |
| Frontend progress UX | **Recommended** — staged progress indicator, since stages are now individually measured |

---

## 5. Prerequisites before any training run

1. A labelled Morisyen intent set larger than the current 32 evaluation cases, with a
   held-out split (dataset-leakage test already exists).
2. A compact-prompt evaluation harness, so the objective "hold intent accuracy at a small
   prompt size" is measurable before and after.
3. An uncertainty-calibration label set, if objective 3 is pursued.
4. Re-run `run_structured_experiments.py` to confirm enum validity has not regressed on
   whatever model version is current at that time.

---

## 6. Summary

| Question | Answer |
|---|---|
| Train for schema formatting? | **No** — 100% exact enum validity, 0 enum coercions in 110 requests |
| Train for Morisyen intent under a compact prompt? | **Yes** — the top measured gap (100% → 53.8%) |
| Train for tool-argument formatting? | **No** — no observed defect |
| Will training fix latency? | **No** — latency is routing/config/UX, already improved ≈69% |
| Train in this step? | **No** — Step 2 is measurement and configuration only |
