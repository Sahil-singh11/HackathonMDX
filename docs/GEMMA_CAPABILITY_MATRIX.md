# Gemma 4 Hosted Capability Matrix — `gemma-4-26b-a4b-it`

**Consolidation, plus exactly one live call.** Sections 1–5 are consolidation only — zero new
API calls, every row citing where the number was measured, nothing asserted from memory or
vendor docs alone. **§6 is the one exception**: a single pre-approved `client.models.list()`
enumeration run on 30 Jul 2026 to close the last open item of Task 1b step 1. Anything still
not measured says so explicitly (§7).

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

## 6. Model availability for this key — ENUMERATED (30 Jul 2026)

Task 1b step 1, finally run: one pre-approved `client.models.list()` call, `google-genai`
2.14.0, **1 399 ms**, **56 models** returned. The brief's instruction was *discover, don't
assume* — this is the discovery, and it corrects two things this document previously had to
leave open.

**Gemma models exposed to this key: exactly two.**

| Model ID | Input tokens | Output tokens | Supported actions |
|---|---|---|---|
| `models/gemma-4-26b-a4b-it` | **262 144** | 32 768 | `generateContent`, `countTokens` |
| `models/gemma-4-31b-it` | **262 144** | 32 768 | `generateContent`, `countTokens` |

Full list by family: gemini 40 · gemma 2 · veo 3 · imagen 3 · deep 3 · lyria 2 · nano 1 ·
antigravity 1 · aqa 1.

Three findings that matter:

1. **No hosted E2B or E4B variant exists on this key.** Nothing matching `e2b`, `e4b`, `nano`
   or `edge` is in the Gemma family here (the one `nano-*` hit is `nano-banana-pro-preview`,
   an image model). The edge tier was therefore *never* reachable through the hosted API — it
   could only ever have been served locally, which is exactly what §8 measured and rejected.
   This retires the "try E2B/E4B hosted" idea rather than leaving it as an untried option.
2. **`gemma-4-31b-it` is available and was never evaluated.** It is the only untried Gemma
   upgrade path on this key. Its behaviour is **not measured** — see §7.
3. **Context window is 262 144 tokens (256K) input**, not the 128K that family documentation
   suggested for edge variants. Production prompts are ≤ a few thousand tokens, so the
   headroom is ~2 orders of magnitude. This is a declared limit from the API, not a
   behavioural measurement: quality at depth is untested (§7).

Neither model advertises any action beyond `generateContent` / `countTokens` — no batch,
cache, or embedding action is declared for Gemma on this key.

```bash
# reproduce (one call, ~1.4 s, negligible quota):
#   python -c "import google.genai as g,os;print([m.name for m in g.Client(api_key=os.environ['GEMINI_API_KEY']).models.list() if 'gemma' in m.name])"
```

## 7. Explicitly NOT measured (each would need live calls — ask before spending quota)

1. ~~Model-list enumeration for this key~~ — **done, §6.**
2. **`gemma-4-31b-it`** — confirmed available (§6), behaviour never probed: no accuracy,
   latency, structured-output or function-calling numbers. The one open upgrade path.
3. Audio input on either hosted Gemma variant.
4. Long-context *behaviour*. The 256K input limit is now a known declared figure (§6), but
   quality at depth is untested — and per §9 the edge tier is a closed negative result, so
   the "what fits on-device" question is moot. Worked through in full in **§10**.
5. Interactions API behaviour for this model.
6. Batch/caching endpoints — not declared for Gemma on this key (§6), so likely unavailable
   rather than merely unprobed.

## 8. Re-verification one-liners (each spends quota — get approval first)

```bash
# live gates (10 checks):        GEMINI_API_KEY=... backend/.venv/bin/python backend/scripts/run_gemma_gates.py
# live test tier (8 tests):      GEMINI_API_KEY=... backend/.venv/bin/python -m pytest -m live -v
# conversational baseline (~40): backend/.venv/bin/python evaluation/run_all.py --provider hosted
# real-photo benchmark (52):     backend/.venv/bin/python evaluation/species_benchmark.py
```

## 9. Local tier — Gemma 4 E2B via Ollama: measured negative result (30 Jul 2026)

**Setup.** Ollama 0.32.5 (user-space install), WSL2 Ubuntu, RTX 3060 Laptop 6 GB VRAM, 3.6 GB free system RAM. Model `gemma4:e2b-it-q4_K_M` — **7.2 GB on disk vs ~1.3 GB in the planning brief**; `nvidia-smi` showed 2 829 / 6 144 MiB resident while serving, i.e. partial CPU offload from the start.

| Probe | Result | Wall clock |
|---|---|---|
| Negative control — identical prompt, **no image** | **PASS** — model replied "Please provide an image…"; the runtime is not silently dropping image parts and confabulating | 28.2 s |
| Positive probe — `data/demo/octopus_cyanea_151112387.jpg`, cold | Vision **functional**: described real content (deep reddish-brown skin, wrinkled texture, clear blue water, rocky substrate) — but identified the animal as "marine mammal (likely a sea lion or seal)": a **confident misidentification of the flagship demo species** | 15.9 s |

**Conclusion.** Local E2B vision inference works mechanically but is neither fast enough nor accurate enough for default use on team hardware: 15.9 s cold against the 10.1 s hosted median, and a false-confident error on the primary demo species against a hosted baseline of 0.865 top-1 / 2.1 % false-confident. The failure mode (confident, structured, wrong) is precisely the one this application must not ship.

**Decision.** Hosted Gemma 4 26B A4B remains the default provider — a conclusion the AI workstream has since reached independently on the fine-tune path too: the targeted E2B QLoRA v2 adapter fixed `make_declaration` recall (0.455 → 1.000) but FAILED its pre-registered tool-accuracy gates and was REJECTED (docs/AI_STEP4_FINAL_REPORT.md, docs/AI_FINAL_HANDOFF.md). The offline story is carried by the browser text tier (offline assistant). `gemma_local.py` remains the honest `LocalUnavailable` stub from Task 1a. Future paths, in preference order: the `e2b-it-qat` quantisation-aware build, a fine-tune on Mauritian species imagery, or Jetson-class edge hardware.

**Follow-up, resolved.** Model-list enumeration — deferred from this session because DNS was starved during the model pull — has since been run: see §6. It confirms the conclusion above from a second direction, because **no hosted E2B/E4B variant is exposed to this key at all**. Local serving was the only way to reach the edge tier, and it failed on accuracy. The remaining untried Gemma path on this key is `gemma-4-31b-it` (§7.2), which is a *larger* hosted model — not an edge one.

## 10. Long context — the question, re-scoped (Task 4c)

Task 4c asked for a measured answer to: *what is the largest document Gemma 4 E2B
handles locally at acceptable latency on team hardware, and at what size does quality
collapse?*

**That question is moot, and saying so is the honest deliverable.** Two independently
measured findings retire it:

1. **§9 — the local tier is a closed negative result.** E2B via Ollama on an RTX 3060
   6 GB gave 15.9 s cold and a false-confident misidentification of the flagship demo
   species. It is not the default and is not shipping.
2. **§6 — no hosted E2B or E4B is exposed to this key.** The edge tier was never
   reachable through the hosted API either.

So "what fits on-device" has no deployment it would inform. Measuring it would produce a
number about a tier we do not ship — and this document's rule is that every row is a
number someone could act on. **No new measurements were taken for this section.**

### What is known instead, and why it settles the document-heavy pillars

Blue Finance and Marine Biotechnology are document-heavy, which is what made 4c worth
asking. The enumeration in §6 already answers it for the tier those pillars will
actually run on:

| | Value | Source |
|---|---|---|
| `gemma-4-26b-a4b-it` input limit | **262 144 tokens** | §6 (enumerated, 30 Jul 2026) |
| `gemma-4-31b-it` input limit | **262 144 tokens** | §6 (enumerated, never evaluated) |
| Output limit, both | 32 768 tokens | §6 |

Against our actual prompts, measured by reading the repo — **exact character counts, not
estimates**:

| Prompt | Characters | Source |
|---|---|---|
| `SYSTEM_INSTRUCTION` (production) | 2 267 | `backend/app/prompts/system.py` |
| `COMPACT_SYSTEM_INSTRUCTION` | 1 095 | `backend/app/prompts/system.py` |
| Species rules catalogue (largest data blob in a prompt) | 4 210 | `data/rules/species_rules.json` |
| Transport pillar brief prompt | 1 751 | `backend/app/pillars/transport/brief.py` |

The largest is ~4.2 K characters. Against a 262 144-token window the headroom is roughly
**two orders of magnitude**. Context length is not a constraint on any pillar we have
built or planned.

**Token counts are deliberately not asserted.** `countTokens` is a supported action on
both models (§6) but running it spends quota, so the table reports characters, which are
exact, rather than a tokeniser estimate dressed up as a measurement.

### Still unmeasured

- **Quality at depth.** 262 144 is a *declared API limit*, not a behavioural result. We
  have never sent a long document and checked whether the answer degrades. If a pillar
  ever pushes past a few thousand tokens, that becomes a real question again.
- **`gemma-4-31b-it` entirely** (§7.2) — available on this key, never evaluated.
- The real constraint on Blue Finance and Biotech is not context length but whether an
  uploaded document may be sent to a hosted model at all under this project's privacy
  rules. That is a Workstream 3 decision, not a model capability limit, and this document
  takes no position on it.

## 11. Transport narrative — four live calls, three failure modes, no success (30 Jul 2026)

The Marine Transport pillar asks the hosted model for one thing: a few sentences of prose
about numbers that are already computed. **It has never once succeeded.** Recorded here
because a capability that fails in three different ways is a capability finding, and because
the next person to try deserves the map rather than the conclusion.

| # | Configuration | Outcome | Wall clock |
|---|---|---|---|
| 1 | fisheries instruction, 60 s | `503 UNAVAILABLE` — "model is currently experiencing high demand" | ~9.6 s |
| 2 | fisheries instruction, 60 s | **Refusal**, in the catch-assistant JSON envelope: *"I am an analysis engine for fishers, not a port officer."* | 5.7 s |
| 3 | transport instruction (2 paragraphs), 60 s | Read timeout | 62.8 s |
| 4 | transport instruction (~4 sentences), 90 s | Read timeout | 92.3 s |

**What each call ruled out.**

- Call 2 identified the cause of call 2 and produced a fix (decision log 17): the provider's
  `chat()` carried the fisheries system instruction, which both scopes the model to fisher
  assistance and orders structured output. That failure mode is fixed and pinned as a
  regression test. **It has not recurred.**
- Calls 3 and 4 together **reject the latency hypothesis by experiment.** If the brief were
  merely long, cutting it from two paragraphs to four sentences *and* raising the ceiling by
  50% should have landed it. It did not — the request ran to the new ceiling exactly as it
  ran to the old one. The 90 s bump was therefore reverted as net-harmful: it bought no
  success and cost every caller 30 s more waiting before the identical fallback.

**What this does NOT establish.** Four calls is a small sample against a model whose own
documented residual risk is ~1.5% of requests running long (§5), and call 1 proves the
endpoint was under real demand pressure that day. The honest reading is *"unexplained, with
the two cheapest explanations eliminated"* — not *"the model cannot do this."*

**Next diagnostic, for whoever picks it up.** Do not raise the timeout again; that has been
tried. Call `chat()` directly with the transport instruction and a two-line payload, outside
the pillar, and see whether a minimal prompt returns at all. That separates "this model, this
instruction" from "this prompt size" from "that day's capacity" for the cost of one request.

**Meanwhile the product is unaffected and honest.** Every response carries
`narrative_source: "deterministic_fallback"` with the real reason in `narrative_note`, and
the numbers a port officer actually needs — arrivals, ETAs, congestion — are computed
deterministically and were never at risk from any of this.
