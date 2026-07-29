# Gemma 4 Hosted Capability Matrix — `gemma-4-26b-a4b-it`

**Consolidation only — zero new API calls.** Every row cites where the number was measured;
nothing here is asserted from memory or vendor docs alone. This is Task 1b's capability
matrix assembled from evidence that already exists in this repository. Anything not
measured says so explicitly.

- SDK: `google-genai` 2.14.0 · API path: `client.models.generate_content`
- Primary evidence: `docs/AI_PRODUCTION_CONFIG_DECISION.md` (110 instrumented requests,
  Step 2), `docs/GEMMA_GATES.md` + `docs/GEMMA_LIVE_GATE_REPORT.md` (live gates, 29 Jul),
  `evaluation/results/{structured_output_experiments,latency_stages,sdk_capability_probe,gemma_live_gates}.json`,
  `evaluation/results/species_benchmark.json` (52 real photos), `docs/BASELINE_REPORT.md`.

## 1. Input / output modalities

| Capability | Verdict | Measured evidence | Source |
|---|---|---|---|
| Text in | ✅ works | 10/10 live gates; 110 Step-2 requests | GEMMA_GATES.md; AI_PRODUCTION_CONFIG_DECISION.md |
| Image in (JPEG) | ✅ works | Real-photo benchmark over 52 licensed images: **0.865 top-1** (0.938 when answered, 2.1% false-confident); image-structured stage median 5 202 ms | species_benchmark.json; latency_stages.json |
| Morisyen (Kreol Morisien) | ✅ works | 96.9% intent on the 32-case conversational suite; Morisyen gate PASS; native Morisyen replies throughout | BASELINE_REPORT.md; GEMMA_GATES.md |
| Audio in | ❓ **not probed** | Family documentation attributes audio to E2B/E4B only; never attempted against 26B with this key | — |
| Output | text only | consistent with family documentation; all observed responses text/JSON | all runs |

## 2. Structured output — the decisive Step-2 experiment (110 requests)

| Mechanism | Verdict | Final valid / exact enums | Latency | Source |
|---|---|---|---|---|
| **Prompt-instructed JSON + boundary coercion** | ✅ **PRODUCTION** | **100% / 100%** (intent 100%) | median 4 648 ms, p90 8 250 ms | config A, AI_PRODUCTION_CONFIG_DECISION.md §1–2 |
| `response_json_schema` | ⚠️ works, rejected | 72.7% / 59.1% | p90 **53.5 s** — intermittently writes to the output ceiling | configs B/C |
| `response_schema` = transport Pydantic | ❌ pathological | one probe ran **725 531 ms**, emitted 32 768 tokens (ceiling), `parsed=None`; another returned `finish_reason=RECITATION`, empty text | §5 |
| `response_schema` = application model | ❌ unbuildable | SDK rejects `Literal[True]` invariants (`ValueError`) | §5 |
| `response_format` | ❌ does not exist | absent from `GenerateContentConfig` in google-genai 2.14.0 (verified by introspection); **not run, no fabricated result** | §5 |
| Interactions API | ❓ not established | `client.interactions` exists; Gemma 4 availability/function-calling through it never validated | §5 |

Enum adherence correction (§4): across all 110 Step-2 requests, **enum coercion fired 0
times** — the Step-1 "unreliable enums" finding was an artifact of a thinner schema hint.

## 3. Thinking control — answers the brief's open question

| Control | Verdict | Evidence | Source |
|---|---|---|---|
| `thinking_budget` (incl. 0) | ❌ rejected by API | `400 INVALID_ARGUMENT — Thinking budget is not supported for this model` (matches the Step-0 gate WARN) | §5; GEMMA_GATES.md |
| `thinking_level=MINIMAL` | ✅ accepted; pays on **tool selection only** | bare-prompt probe **733 ms vs 11 483 ms**; end-to-end, MINIMAL-everywhere (config F) was *slower* than default (5 812 vs 4 648 ms median) | §1–2 |
| `thinking_level=HIGH` | ❌ worse on every axis | 59.1% validity, median 28 007 ms, max 151 202 ms; no accuracy gain on images | §5 |
| Hidden thought tokens | measurable | `usage_metadata.thoughts_token_count` recorded per request in diagnostics | structured.py; hosted diagnostics |
| **`max_output_tokens`** | ❌ **never in production** | with default thinking, caps of 256/384/1024 all returned `finish_reason=MAX_TOKENS` with **empty text** — hidden thinking consumes the budget. Bounding thinking does **not** make caps safe: the capped `response_json_schema` configs still ceiling-ran. Production runs uncapped behind per-route timeouts (45 s tools · 60 s text · 75 s image) | §2 "Output cap", §5; commit 288639e |

## 4. Function calling

| Aspect | Verdict | Evidence | Source |
|---|---|---|---|
| Native function calling | ✅ works | live gate PASS; weather probe requests `get_marine_conditions` with validated args | GEMMA_GATES.md; test_hosted_integration.py (live tier) |
| Tool-response round trip | ✅ works | measured end-to-end: weather route 14 016 ms total incl. 2 015 ms tool execution | AI_PRODUCTION_CONFIG_DECISION.md §3 |
| Schema + function_call on one turn | ⚠️ **compete** | a response schema and a `function_call` part fight for the same output → production uses a **two-turn lifecycle** (unstructured tool-selection turn, then structured final turn) | gemma_hosted.py docstring |
| Injection resistance | ✅ held in every test | 100% safety pass across all 110 Step-2 requests; live injection gate: no unknown function, no key material in output | §3; test_hosted_integration.py |

## 5. Latency (production configuration, measured)

| Route | Total | Source |
|---|---|---|
| Text-only catch logging | 8 296 ms | AI_PRODUCTION_CONFIG_DECISION.md §3 |
| Image species analysis | 11 889 ms | §3 |
| Weather with tool round trip | 14 016 ms | §3 |
| **Median (post-optimisation)** | **10 092 ms** — ≈69% below the ≈33 s Step-1 baseline | §3 |
| Residual risk | ~1.5% of requests can still run long (one 52.8 s outlier in 66 requests); mitigated by per-route timeouts → repair → safe-uncertain → disclosed mock | §6 |

Image sizing: **1280 px longest side is kept** — reducing to 768 px measured *slower*
(6 483 vs 6 281/5 250 ms) with no accuracy gain; 1024 vs 1280 inconclusive (§2).

## 6. Explicitly NOT measured (each would need live calls — ask before spending quota)

1. **Model-list enumeration for this key** (`client.models.list()`) — the brief's 1b step 1. One cheap call; never run.
2. Other Gemma 4 variants (E2B/E4B/12B/31B) via the hosted API with this key.
3. Audio input on any hosted variant.
4. Long-context behaviour (family docs claim 128K on edge variants; our prompts are ≤ a few thousand tokens).
5. Interactions API behaviour for this model.
6. Batch/caching endpoints.

## 7. Re-verification one-liners (each spends quota — get approval first)

```bash
# live gates (10 checks):        GEMINI_API_KEY=... backend/.venv/bin/python backend/scripts/run_gemma_gates.py
# live test tier (8 tests):      GEMINI_API_KEY=... backend/.venv/bin/python -m pytest -m live -v
# conversational baseline (~40): backend/.venv/bin/python evaluation/run_all.py --provider hosted
# real-photo benchmark (52):     backend/.venv/bin/python evaluation/species_benchmark.py
```
