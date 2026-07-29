# AI Model Selection Decision Record

Final state, 2026-07-30. This record explains **why each model is where it is** and what
evidence would change the decision.

---

## Decision 1 — Production: hosted `gemma-4-26b-a4b-it`

**Role:** Morisyen/English understanding, function selection, structured application
responses, and catch-image analysis. The only model in the production path.

**Why:**
- Passed all 10 live capability gates on real inference (Step 1): English, Morisyen,
  image, image+Morisyen, structured output, function selection, Open-Meteo tool round
  trip, prompt injection, failure handling, latency.
- 100% final schema validity and 100% safety across 110 Step-2 experiment requests and
  every later evaluation.
- Multimodal: the only candidate that can do constrained catch-photo analysis.

**Configuration (measured, Step 2):** prompt-instructed JSON beat native
`response_json_schema` on this model (100% vs 72.7% validity; the native path
intermittently generates to the token ceiling). Full system prompt retained (the compact
prompt cost intent accuracy). Two-turn tool lifecycle with a lean first turn; median
end-to-end latency 33 s → ~10 s with no model change.

## Decision 2 — Experimental, disabled: `google/gemma-4-E2B-it` + QLoRA adapter

**Role:** none in production. Candidate compact-prompt Morisyen router, evaluated twice.

**Why it exists:** hosted routing under a compact prompt measured 70.6% intent at 18.5 s
median — a local 3.94 B router promised better accuracy, 4× lower latency, offline
capability, and one fewer hosted call per request.

**Why it is disabled:** it failed the pre-registered v2 acceptance gates.

| Evidence | v2 adapter | Bar |
|---|---|---|
| Internal intent | 85.3% | ≥85% ✔ |
| External intent | 78.1% | ≥80% ✘ |
| Tool accuracy | 58.8% | ≥80% (full) / ≥70% (hybrid) ✘ |
| Min critical-intent recall | 66.7% | ≥75% ✘ |
| Structured validity / safety / latency / reload | 100% / 100% / 4.6 s / deterministic | all ✔ |

The gates were committed before training and were not adjusted afterwards. **Training
succeeded, but the adapter did not pass the production acceptance gate.**

**What would change this:** a v3 adapter that clears the same class of gate — the
identified work is the tool-selection head (flat at 58.8% across v1 and v2), a ≥100-record
internal test so per-intent floors aren't decided by single records, and completing the
Morisyen review.

## Decision 3 — Rejected alternatives (with the evidence)

| Alternative | Why rejected |
|---|---|
| Gemini or any non-Gemma model | Out of scope by competition and project constraint; never substituted, enforced by assertions in every runner |
| Native structured output (`response_schema` / `response_json_schema`) on 26B | Measured worse: Pydantic path pathological (32 768-token runaway, RECITATION); JSON-schema path 72.7% validity, p90 53.5 s |
| Compact prompt on hosted 26B | Intent accuracy 100% → 53.8%; the dropped guidance is load-bearing — became the *training objective* instead |
| `local` provider mode as production | No local model loaded; the provider honestly reports unavailable rather than simulating edge inference |
| Enabling the v1 adapter (73.5%) | Failed its gate (Step 3); superseded by v2, also rejected |
| Hybrid fast-path for `make_declaration` only (P/R 1.000/1.000) | The hybrid gate's overall tool bar (70%) failed at 58.8%; enabling one intent while the tool head misroutes functions would execute wrong actions with high confidence |
| P100 as the training accelerator | sm_60: bitsandbytes 4-bit kills the process; torch 2.10+cu128 ships no sm_60 kernels at all. T4 (sm_75) is mandatory and enforced in-notebook |

## Fallback order (production, unchanged)

hosted `gemma-4-26b-a4b-it` → one controlled repair → safe uncertain response →
deterministic mock **with visible disclosure**. The fine-tuned router is not in this
chain and cannot silently enter it: it has no provider-mode value, `readiness()` reports
the failed gates by name, and `route()` raises `RouterUnavailable`.
