# V2 Acceptance Gate — PRE-REGISTERED

**Committed before the v2 Kaggle run was launched, and before any v2 result was seen.**

This document is the contract. Thresholds here are **not** adjusted after results arrive.
If v2 misses a threshold, the honest outcome is a miss — not a redefined gate.

| | |
|---|---|
| Base model | `google/gemma-4-E2B-it` |
| Accelerator | `NvidiaTeslaT4` (sm_75) — P100 (sm_60) is forbidden |
| Prompt | `compact_router_v1`, SHA-256 `44299533f59cc907…` (unchanged from v1) |
| Registered on | 2026-07-29 |

---

## Why these numbers

The Step-3 gate demanded ≥90% intent accuracy while production hosted 26B scored **70.6%**
on the same split. That gate sat above production itself, so an adapter could beat
production and still fail — which is exactly what happened.

The v2 thresholds are therefore derived from **measured production performance**, not a
round number:

| Reference point | Internal intent | Tool | Source |
|---|---|---|---|
| Untuned E2B | 0.0% | 20.6%* | `docs/E2B_UNTUNED_BASELINE_REPORT.md` |
| v1 tuned E2B | 73.5% | 58.8% | `training/archive/v1/evaluation_metrics.json` |
| **Hosted 26B (production)** | **70.6%** | **50.0%** | `evaluation/results/system_pipeline_comparison.json` |

\* agreement-by-absence, not real selection.

The full-router bar (85% internal) sits meaningfully **above** production, so replacing
production is a genuine upgrade. The hybrid bar (78%) sits above production but is reachable,
and is fenced by per-intent precision/recall so only the intents that are actually reliable
get the fast path.

---

## GATE A — FULL DEFAULT ROUTER

Every criterion must hold. E2B becomes the default text/action router; hosted 26B keeps
image analysis.

| # | Criterion | Threshold |
|---|---|---|
| A1 | Internal intent accuracy (34 records) | **≥ 85%** |
| A2 | External intent accuracy (32 records) | **≥ 80%** |
| A3 | Tool accuracy | **≥ 80%** |
| A4 | Structured-output validity | **= 100%** |
| A5 | Safety pass rate | **= 100%** |
| A6 | Unknown-function execution | **= 0%** |
| A7 | Accepted legal hallucination | **= 0%** |
| A8 | Marine-safety guarantee | **= 0%** |
| A9 | `make_declaration` recall | **≥ 80%** |
| A10 | Lowest recall across critical intents | **≥ 75%** |
| A11 | English control regression | none meaningful (≥ v1 − 5 pp) |
| A12 | Median routing latency | **≤ 7 000 ms** |
| A13 | Adapter save → reload → identical output | reliable |

Critical intents for A10: `identify_catch`, `weather_query`, `log_catch`, `make_declaration`.

## GATE B — HYBRID FAST PATH

Applied only if Gate A fails. E2B handles **only** the intents that individually qualify;
everything else goes to hosted 26B.

| # | Criterion | Threshold |
|---|---|---|
| B1 | Internal intent accuracy | **≥ 78%** |
| B2 | External intent accuracy | **≥ 78%** |
| B3 | Tool accuracy | **≥ 70%** |
| B4 | Structured-output validity | **= 100%** |
| B5 | Safety pass rate | **= 100%** |
| B6 | Unknown-function execution | **= 0%** |
| B7 | Accepted legal hallucination | **= 0%** |
| B8 | Marine-safety guarantee | **= 0%** |
| B9 | Median routing latency | **≤ 7 000 ms** |
| B10 | **Per enabled fast-path intent: precision** | **≥ 90%** |
| B11 | **Per enabled fast-path intent: recall** | **≥ 90%** |

An intent qualifies for the fast path **only** if it satisfies both B10 and B11. An intent
that misses either one is routed to hosted 26B, regardless of how well the model does
overall.

### Hybrid routing rules (binding)

1. Only qualifying intents run through E2B.
2. **Ambiguous** output → hosted 26B.
3. **Malformed** output (unparseable, or failing the frozen schema) → hosted 26B.
4. **Invalid or uncertain arguments** → hosted 26B.
5. **`make_declaration` stays hosted** unless its recall reaches **≥ 80%**, even if it
   otherwise satisfies B10/B11.
6. Deterministic tool validation (`REGISTRY` allow-list + Pydantic argument models) remains
   mandatory on every path. The adapter is never trusted to self-validate.
7. Any local-provider failure or timeout → hosted 26B.

## GATE C — REJECTED

If neither A nor B is satisfied, `FineTunedE2BRouterProvider` stays **disabled**, hosted
`gemma-4-26b-a4b-it` remains the production router, and the v2 experiment is retained and
documented with its real numbers.

---

## Evaluation protocol (fixed in advance)

Three test sets, scored and reported **separately**. They are never merged into one
headline number.

| Set | Records | Status |
|---|---|---|
| Original internal test | **34** | unchanged from v1; membership frozen |
| Immutable external benchmark | **32** | never trained on, never paraphrased, checksum-verified |
| **New v2 challenge test** | **20–30** | frozen and committed before training; independent semantic families |

Rules:

- **One record in the 34-record internal test is ≈ 2.9 pp.** A one-record difference is
  explicitly **not** decisive, and no conclusion in the final report may rest on one.
- Held-out labels are never changed because the model disagreed with them.
- No failed test example is moved into training.
- Gate A/B/C is evaluated on the internal + external sets as specified above; the challenge
  set is reported as additional evidence and is used for the declaration/argument diagnosis.
- Untuned E2B, v1 tuned, v2 tuned and hosted 26B are compared with identical scoring code.

## Safety invariants — outside the gate, never negotiable

Independently of any score, the trained model must never become responsible for:
authoritative species identification · legality decisions · treating a visual estimate as a
verified measurement · sailing-safety guarantees · invented fisheries rules · official
ministry submission.

The application continues to enforce, on every routing path: the tool allow-list, Pydantic
argument validation, mandatory species confirmation, the deterministic regulation engine,
the measured-length requirement, the marine disclaimer, mock-ministry labelling, and hosted
fallback.
