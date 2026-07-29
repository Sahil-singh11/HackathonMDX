# AI Step 2 — Experiment Plan (Native Structured Output + Latency)

Branch: `ai-modeling` · Model: `gemma-4-26b-a4b-it` · SDK: `google-genai` 2.14.0 ·
Python 3.12.2 · Pydantic 2.13.4

Goal: replace prompt-instructed JSON with the strongest **genuinely supported** native
structured-output mechanism, and cut latency without weakening safety, correctness or
function selection. No fine-tuning in this step. `coerce_to_schema()` stays as the final
boundary fallback.

> Branch note: `ai-modeling` had been left at the Step-1 commit `f3dbfb9` while `main`
> advanced to `ec9215e` (which already contains `f3dbfb9`, plus teammate backend hardening:
> rate limiting, marine pre-warm, OpenAPI examples). `ai-modeling` was **fast-forwarded** to
> `ec9215e` before this step — no commits were lost or rewritten.

---

## 1. Current implementation (measured, not assumed)

### 1.1 SDK surface — `google-genai` 2.14.0

Introspected from the installed package (`types.GenerateContentConfig.model_fields`):

| Config field | Present in installed SDK |
|---|---|
| `response_mime_type` | **yes** (`Optional[str]`) |
| `response_schema` | **yes** (`dict \| type \| types.Schema \| ...`) |
| `response_json_schema` | **yes** (`Optional[Any]`) |
| `response_format` | **no — does not exist in this version** |
| `thinking_config` | **yes** (`Optional[ThinkingConfig]`) |
| `max_output_tokens` | **yes** (`Optional[int]`) |
| `media_resolution` | yes (`MEDIA_RESOLUTION_LOW/MEDIUM/HIGH`) |
| `tools`, `tool_config`, `system_instruction`, `temperature`, `seed`, `http_options` | yes |

`ThinkingConfig` fields: `include_thoughts`, `thinking_budget`, `thinking_level`.
`ThinkingLevel` enum: `MINIMAL`, `LOW`, `MEDIUM`, `HIGH` (+ `UNSPECIFIED`).

`GenerateContentResponse.parsed` **exists as a model field** (not a property), alongside
`usage_metadata`, which exposes `prompt_token_count`, `candidates_token_count`,
**`thoughts_token_count`**, `total_token_count`.

`client.interactions` **exists** on the client object. Its viability for this model is
probed, not assumed — see §6.

### 1.2 Current structured-output path (the control)

`backend/app/providers/hosted.py`: `generate_content` with `system_instruction`, `tools`,
`temperature=0.2`, `http_options(timeout=60s)` — and **no** `response_mime_type`, **no**
`response_schema`. The JSON shape is described in the prompt (`RESPONSE_SCHEMA_HINT`), then
recovered by the ladder: native parse → fenced regex → one repair request → safe uncertain
fallback. `coerce_to_schema()` normalises enums at the boundary.

**Named control configuration: `control_prompt_json_coercion`.**

### 1.3 Current thinking mode

**Unset — which is not "off".** Baseline probes with no `thinking_config` burned
**380–475 thought tokens on a one-line prompt** (11.5 s and 10.0 s). Thinking is on by
default and is a primary latency cost. `thinking_level=MINIMAL` returned in 5.5 s with
`thoughts_token_count = None`.

### 1.4 Current prompt sizes

| Component | Chars | ≈ tokens |
|---|---|---|
| `SYSTEM_INSTRUCTION` | 2 267 | ≈ 566 |
| Candidate block (6 of 5 catalogue species, full `public_candidate`) | 1 528 | ≈ 382 |
| `RESPONSE_SCHEMA_HINT` | ≈ 560 | ≈ 140 |

The catalogue is small (5 species), so "don't send the whole database" is already partly
satisfied by `candidates_for()` — but every candidate carries its full
`visible_characteristics` list, which is the bulk of those 382 tokens.

### 1.5 Current output limit

**None.** `max_output_tokens` is deliberately unset, with this comment in `hosted.py`:

> No max_output_tokens: this model emits hidden (thinking) tokens first, so a cap can
> consume the whole budget and return empty text (observed finish_reason=MAX_TOKENS with
> len 0).

That prior finding is treated as a hypothesis to re-measure, not a fixed rule — the
interaction between `max_output_tokens` and `thinking_level=MINIMAL` is the experiment.

### 1.6 Current image dimensions and compression

`backend/app/services/vision/quality.py`: EXIF-transposed, RGB, `thumbnail((1280, 1280))`
(aspect preserved), JPEG **quality 85**. `MIN_DIM = 200`. Quality gate (blur/brightness/
glare) runs **before** any model call, so unusable images never spend tokens.

**Current longest side: 1280 px.**

### 1.7 Current function-call flow

`hosted.py` loops up to 4 rounds: `generate_content` → if any part carries a
`function_call`, validate+execute via the allow-listed `REGISTRY`, append the tool response,
repeat; otherwise take the text as final. Step 1 proved the two-turn lifecycle works on real
inference (gate 6 + gate 7).

### 1.8 Current retry/repair flow

Exactly one repair request when the final text yields no JSON, then the safe uncertain
fallback. Dispatcher catches any hosted exception and falls back to the disclosed mock.

### 1.9 Current latency instrumentation

Single end-to-end `latency_ms` per provider call, plus `capabilities.record_hosted_latency()`.
**Gap:** one full tool round trip is recorded as one number, so first-turn, tool, and
second-turn costs are indistinguishable. Step 2 adds staged timing.

### 1.10 `coerce_to_schema()`

`backend/app/schemas/gemma_gate.py`. Pins `species_confirmation_required` and
`measured_size_required` to `True`, forces `species_id` into the candidate shortlist, forces
`requested_function` into `REGISTRY`, and falls out-of-enum values back to the safest option
(`other` / `low` / `confirm_species`). **Retained unchanged as the final boundary.**

### 1.11 Relevant tests

`backend/tests/test_ai_provider.py` (35 offline), `test_hosted_integration.py` (8 real),
`test_tools_registry.py`, `test_api_flow.py`, `test_privacy_and_hygiene.py`. Step-1 baseline:
**93 passed, 0 failed** — no regression permitted.

---

## 2. Decisive early findings (already measured on the real model)

These reshaped the plan before the matrix was written.

**Finding A — `response_schema=<Pydantic app schema>` cannot even be built.**

```
ValueError: Literal values must be strings.
```

`GemmaStructuredAnalysis` pins two invariants as `Literal[True]`. The SDK's schema
converter rejects non-string `Literal`s. → A **transport model** is required (§4).

**Finding B — `response_schema=<Pydantic transport model>` is pathological on this model.**
It "succeeds" but ran **725 531 ms (≈12 min)**, emitted **32 768 output tokens** (the
ceiling), and left `parsed = None`. It degenerates rather than terminating. **This is a
failure mode, not a slow success**, and it is why every probe is now hard-bounded at 90 s.

**Finding C — `response_json_schema=<dict>` works well.**
**3 766 ms**, **147 output tokens**, `parsed` populated **as a `dict`**, body valid JSON in
the requested shape. This is the strongest genuinely-working mechanism.

**Finding D — `response.parsed` is real but returns a `dict` here**, not a
`GemmaTransportAnalysis`. The adapter therefore accepts either shape and validates a dict
itself, rather than assuming an SDK-constructed model.

**Finding E — `response_mime_type` alone works but does not constrain shape**
(returned `{"response": "..."}` — valid JSON, wrong schema). Necessary, not sufficient.

**Finding F — default thinking is expensive**: 380–475 thought tokens on a trivial prompt.

**Finding G — `response_format` does not exist in this SDK version.** Config D is therefore
**not runnable as specified** and will be reported as unsupported, not fabricated.

---

## 3. Experiment matrix

At least **20 representative requests** per configuration, balanced across: English catch
registration, Morisyen catch registration, image species suggestion, image + Morisyen,
low-quality/uncertain image, unknown species, weather intent, declaration intent, hostile
injection note, missing information.

| Config | Mechanism | Thinking | Output cap | Prompt |
|---|---|---|---|---|
| **A — control** | `control_prompt_json_coercion` (prompt-only JSON) | current (unset) | none | current full |
| **B — native JSON schema** | `response_mime_type` + `response_json_schema` | `MINIMAL` | bounded | compact |
| **C — native, high thinking** | same as B | `HIGH` | same as B | compact |
| **D — newer response format** | `response_format` | — | — | — |

**Config D will not run**: `response_format` is absent from `GenerateContentConfig` in
google-genai 2.14.0 (Finding G). It is recorded as `unsupported` with the introspection
evidence. The Interactions API is inspected separately (§6) and only tested if it genuinely
supports this model *and* function calling, with rollback available.

`generate_content_pydantic_schema` is retained as a **selectable adapter mode** and probed,
but is expected to be rejected on Finding B evidence.

### Metrics per configuration

raw JSON parse rate · raw schema-valid rate · **exact enum-valid rate** · coercion rate ·
repair rate · final schema-valid rate · safety-rule pass rate · avg / median / **p90**
latency · avg output tokens · avg thought tokens · API failure rate.

---

## 4. Schema design decisions

`GemmaTransportAnalysis` (`backend/app/schemas/transport.py`) is the wire format:

- string `Literal` enums only — **identical accepted values** to the frozen contract;
- one level of nesting (`species_suggestion`), no dicts, no recursion, no unions beyond
  `X | None`;
- bounded lists with field descriptions;
- `species_confirmation_required` / `measured_size_required` are **absent from the wire** —
  they are non-negotiable, so the model is never asked; `to_application_model()` re-asserts
  them.

`to_application_model()` is a deterministic, tested conversion into the frozen
`GemmaStructuredAnalysis`. It re-applies the candidate allow-list and the function
allow-list. **No contract change is hidden in coercion**; the public enum values are
unchanged.

---

## 5. Latency experiments

Staged instrumentation (image preprocessing · first model request · tool execution · second
model request · validation/repair · total), measured separately for text-only,
image, function-selection, tool round trip, and final structured response.

- **A. Thinking level** — `MINIMAL` vs `HIGH` per route. High thinking only where it
  measurably helps ambiguous species reasoning or multi-step tool decisions.
- **B. Output cap** — 256 / 384 / uncapped, explicitly re-testing the empty-output risk
  recorded in §1.5 under `MINIMAL` thinking.
- **C. Prompt compaction** — a compact system instruction keeping every non-negotiable
  safety rule, the candidate restriction, the uncertainty rule, the confirmation
  requirement and the tool policy; dropping schema prose already carried by
  `response_json_schema`. Size measured before/after.
- **D. Image preprocessing** — longest side 768 / 1024 / 1280 (current), aspect preserved,
  compared on accuracy *and* latency on the same cases.
- **E. Candidate context** — shortlist only; measure token reduction and quality.
- **F. Route profiles** — `fast_intent`, `fast_tool_selection`, `image_species_analysis`,
  `final_tool_response`. Collapse to one default if the data shows no meaningful difference.

---

## 6. Interactions API

Inspected only. Tested **only if** the installed SDK supports it for this model, function
calling still works, and rollback is available. Not adopted merely for being newer.

---

## 7. Success criteria

**Structured output** (≥20 requests): raw JSON parse 100% · final schema validity 100% ·
exact raw enum validity ≥95% · coercion ≤5% · no unsafe output · no invented regulation ·
no authoritative species claim.

**Latency**: ≥25% median reduction vs the Step-1 benchmark (median ≈33 s, avg ≈29.8 s); **or**
text/tool-selection median <15 s **and** image-analysis median <25 s.

**Safety**: zero safety regressions · zero unknown-function execution · zero secret leakage ·
zero legal-rule hallucination accepted by application code.

Targets are engineering goals. If unmet, the actual number is reported, the best *safe*
configuration is selected, and demo-loading UX recommendations are written. Nothing is hidden.

---

## 8. Fallback rules

Selection order for the production path, applied explicitly and recorded in diagnostics:

1. `generate_content_json_schema` (Finding C);
2. `generate_content_pydantic_schema` — only if it stops degenerating (Finding B);
3. `prompt_json_fallback` — the Step-1 control, always runnable;
4. `coerce_to_schema()` — final boundary, never removed;
5. safe uncertain response;
6. dispatcher → disclosed mock.

Modes never switch silently: the active mode is recorded in internal provider diagnostics
and is not exposed in the public frontend API.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Pydantic `response_schema` degeneration (32 768 tokens, 12 min) | Hard per-call timeout; mode rejected on evidence; bounded output cap |
| Output cap truncates JSON mid-object | Test 256/384/uncapped and measure `finish_reason`; never ship a cap that truncates |
| `MINIMAL` thinking degrades species reasoning or tool choice | Config C measures HIGH on the same cases; route-specific profiles |
| Native schema mode conflicts with function declarations | Probed directly (`tools_plus_response_schema`); two-turn flow keeps tool selection separate from final structuring |
| Image downscaling loses fish characteristics | Compare accuracy *and* latency on identical cases; do not go below the point features are lost |
| Compact prompt drops a safety rule | Safety rules are asserted by tests, not by prompt review alone |
| Coerced output presented as natively compliant | `native_schema_valid` and `coercion_applied` recorded separately; report never conflates them |
| Private content in evaluation artifacts | Synthetic/redistributable inputs only; no prompts, no images, no chain of thought stored |

---

## 10. Out of scope

Fine-tuning, frontend redesign, database changes, merging to `main`.
