# AI Production Configuration Decision — Step 2

Branch: `ai-modeling` · Model: `gemma-4-26b-a4b-it` · SDK: `google-genai` 2.14.0
Evidence: 110 experiment requests (`evaluation/results/structured_output_experiments.json`),
staged latency benchmark (`evaluation/results/latency_stages.json`), SDK capability probe
(`evaluation/results/sdk_capability_probe.json`).

---

## 1. Headline: the Step-2 hypothesis was rejected by its own experiment

Step 2 set out to replace prompt-instructed JSON with native structured output. **The
measurements say native structured output is materially worse on this model**, so it was
not adopted. The control mechanism is retained, and the latency work was kept where it
independently paid off.

| Config | Mechanism | Prompt | Thinking | Final valid | Exact enums | Intent | Median | p90 |
|---|---|---|---|---|---|---|---|---|
| **A (selected)** | prompt JSON | full | default | **100%** | **100%** | **100%** | **4 648 ms** | **8 250 ms** |
| F | prompt JSON | full | MINIMAL | 100% | 100% | 100% | 5 812 ms | 9 093 ms |
| E | prompt JSON | compact | MINIMAL | 100% | 100% | 53.8% | 4 859 ms | 8 421 ms |
| B | `response_json_schema` | compact | MINIMAL | 72.7% | 59.1% | 70% | 5 233 ms | 53 530 ms |
| C | `response_json_schema` | compact | HIGH | 59.1% | 45.5% | 87.5% | 28 007 ms | 64 139 ms |
| D | `response_format` | — | — | **not runnable** | — | — | — | — |

Safety pass rate was **100% in every configuration**.

---

## 2. Selected production configuration

| Decision | Value | Why |
|---|---|---|
| **API path** | `client.models.generate_content` | Interactions API not validated for this model; no reason to migrate. |
| **Schema mechanism** | `prompt_json_fallback` — JSON described in the prompt, `coerce_to_schema()` at the boundary | Config A: 100% final validity, 100% exact enum validity vs 72.7% / 59.1% for the native schema. |
| **Thinking — tool selection** | `MINIMAL` | The one route where it measurably pays (bare-prompt probe: 733 ms vs 11 483 ms). |
| **Thinking — analysis / final** | model default | Config A (default) beat config F (MINIMAL) end to end, 4 648 ms vs 5 812 ms median. |
| **Output cap** | **none** | On this model `max_output_tokens` also counts hidden thinking tokens: caps of 256/384/1024 all returned `finish_reason=MAX_TOKENS` with **empty text**. |
| **Prompt version** | full `SYSTEM_INSTRUCTION` | The compact prompt halves size but drops intent accuracy from 100% to 53.8%. Retained in code, not used in production. |
| **Turn-1 prompt** | lean (note + language + photo-present flag) | Full context on turn 1 measured 10–19 s; the note alone measures ~4–5 s. |
| **Image longest side** | 1280 (unchanged) | 768 px was *slower* (6 483 ms vs 6 281/5 250 ms) and no more accurate; 1024 vs 1280 was inconclusive because the demo fixtures are already ≤1024. No evidence to change. |
| **Candidate context** | shortlist only, ≤6 via `candidates_for()` | Already the case; `public_candidate()` excludes retrieval-only `keywords`. |
| **Timeouts** | 45 s tool selection · 60 s text/final · 75 s image | Bounded per route; the runaway failure mode makes an unbounded call unsafe. |

### Fallback order (explicit, recorded in diagnostics, never silent)

1. `prompt_json_fallback` (production);
2. `coerce_to_schema()` — the final boundary, **retained unchanged**;
3. one controlled repair request;
4. safe uncertain response;
5. dispatcher → deterministic mock, with `FALLBACK_DISCLOSURE`.

`generate_content_json_schema` and `generate_content_pydantic_schema` remain selectable in
`app.providers.structured` so the decision can be re-tested when the model or SDK changes.

---

## 3. Measured results of the selected configuration

End-to-end through the rewired provider on real inference (post-optimisation):

| Route | Turn 1 | Tool | Turn 2 | Total |
|---|---|---|---|---|
| Weather (tool round trip) | 9 718 ms | 2 015 ms | 4 297 ms | **14 016 ms** |
| Image species analysis | 5 234 ms | 15 ms | 6 655 ms | **11 889 ms** |
| Text-only catch logging | 4 062 ms | — | 4 233 ms | **8 296 ms** |
| Prompt injection | 3 937 ms | — | 3 718 ms | **7 656 ms** |

Median total **10 092 ms**, against a Step-1 benchmark median of ≈33 000 ms — a **≈69%
reduction**. Isolated stage medians (`latency_stages.json`): tool selection 1 422 ms, tool
execution 1 312 ms, final structured response 3 860 ms, text-only structured 3 968 ms,
image structured 5 202 ms, image preprocessing 32 ms.

Correctness on those four live runs: weather → `get_marine_conditions`; image →
`epinephelus_merra` (correct, from the shortlist); text → `log_catch`; injection → **no
function requested, no species claimed**.

### Targets

| Target | Result |
|---|---|
| ≥25% median latency reduction | **Met** — ≈69% (33 000 ms → 10 092 ms) |
| Text / tool-selection median < 15 s | **Met** — text-only total 8 296 ms; tool selection stage 1 422–4 062 ms |
| Image-analysis median < 25 s | **Met** — 11 889 ms |
| Raw JSON parse rate 100% | **Met** for the selected config (A: 100%) |
| Final schema validity 100% | **Met** (A: 100%) |
| Exact raw enum validity ≥95% | **Met** — 100% |
| Coercion ≤5% | **Met on the metric that matters** — enum coercion 0%; see §4 |
| No unsafe output / invented regulation / authoritative claim | **Met** — 100% safety pass across all 110 requests |

---

## 4. An important correction to the Step-1 finding

Step 1 reported that raw output "does not reliably respect the exact enum contract",
citing `intent: "species_identification"`, `confidence_label: "none"`, and prose in
`recommended_next_step`.

**Across 110 Step-2 requests, enum coercion fired 0 times — in every configuration.**

The `coercion_rate` figure looks high for configs A (86.4%) and E (77.3%), but the
per-field record shows `coercion_fields` empty in every one of those cases. That metric
was firing because the raw output failed the *transport* model's `maxLength=220` bound on
`reply`/`reply_morisyen` — a bound invented in Step 2 that the control prompt was never
told about — not because any enum was wrong. This is why `enum_coercion_rate_pct` was
added as a separate metric: the aggregate number was misleading, and acting on it would
have sent training in the wrong direction.

What likely differed in Step 1: the gate runner used a thinner schema hint. The Step-2
hint enumerates `species_suggestion` sub-fields explicitly, and enum adherence is 100%
with it.

**Coerced output is never reported as natively compliant.** `native_schema_valid`,
`exact_enum_valid`, `coercion_applied` and `coercion_fields` are recorded separately per
request, in diagnostics and in the CSV.

---

## 5. Rejected alternatives

| Rejected | Reason |
|---|---|
| `response_schema=<application Pydantic model>` | Cannot be built: `ValueError: Literal values must be strings` (`Literal[True]` invariants). |
| `response_schema=<transport Pydantic model>` | Pathological on this model: one probe ran **725 531 ms** and emitted **32 768 tokens** (ceiling) with `parsed=None`; a later probe returned `finish_reason=RECITATION` with empty text. |
| `response_json_schema` (configs B, C) | 72.7% / 59.1% final validity, 36.4% / 54.5% repair rate, p90 53.5 s / 64.1 s. Intermittently writes to the output ceiling. Bounding the schema with `maxItems`/`maxLength` reduced but did not remove it. |
| HIGH thinking (config C) | Worse on every axis: 59.1% final validity, median 28 007 ms, max 151 202 ms. On the image route in isolation it was no more accurate (3/3 valid either way) and slower (5 567 ms vs 5 275 ms). |
| Compact system instruction (config E) | 51.7% smaller prompt, but intent accuracy fell 100% → 53.8%. The dropped intent/tool guidance is load-bearing. Kept in code, unused. |
| `response_format` (config D) | Does not exist in `GenerateContentConfig` in google-genai 2.14.0 (verified by `model_fields` introspection). **Not run; no fabricated result.** |
| Interactions API migration | `client.interactions` exists, but Gemma 4 availability and function-calling behaviour through that path were not established. Not migrated for novelty. |
| `thinking_budget=0` | Rejected by the API: `400 INVALID_ARGUMENT — Thinking budget is not supported for this model`. Only `thinking_level` works. |
| Output caps in production | With default thinking, 256/384/1024 all produced empty text at `MAX_TOKENS`. |
| Reducing image longest side to 768 | Slower, not faster, and no accuracy gain. |

---

## 6. Residual risk

The native-schema runaway (`MAX_TOKENS` at 1024 tokens, 26–57 s) is a property of this
model that the production path avoids rather than fixes. Config A showed one 11 828 ms
maximum across 22 requests and configs A/E/F together showed one 52 797 ms outlier in 66
requests (~1.5%), so a slow request is still possible. Mitigations in place: per-route
timeouts, one bounded repair, safe uncertain response, and a disclosed mock fallback.

**Demo UX recommendation:** show staged progress ("choosing tools" → "analysing photo" →
"writing your answer") rather than a single spinner, since the stages are now measured
separately and the tool-selection stage returns in ~1.4–4 s.
