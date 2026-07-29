# Lamer Konekte — six blue-economy pillars on one inference spine

**One page for judges.** Every number below was measured and is cited to the file that
records it. Nothing is estimated, rounded up, or carried over from a plan. Where a thing
was *not* measured, this page says so instead of filling the gap.

Written 30 Jul 2026.

---

## What this is

A Gemma 4 platform for Mauritius's blue economy. **One pillar — Sustainable Fisheries &
Aquaculture — is built to production depth** and is what the demo shows. The other five are
declared against the same frozen module contract, three of them implemented, so the claim
"this extends" is a thing you can run rather than a slide.

The spine is two frozen interfaces:

- **`app/inference/base.py`** (Task 1a) — every model call in the system goes through one
  Protocol. Providers are selected by config, health-checked, and every fallback is recorded
  so it can be disclosed rather than silently absorbed.
- **`app/pillars/base.py`** (Task 4a) — every pillar implements the same four methods and
  returns a result carrying a **mandatory, non-nullable `DataProvenance` block**. A pillar
  result that cannot say where its data came from is invalid by construction, not by
  convention. An AST test fails the build if any pillar file imports a model SDK directly.

---

## The three tiers, and which is real

| Tier | What runs | State | Evidence |
|---|---|---|---|
| **Hosted** | `gemma-4-26b-a4b-it` via `google-genai` 2.14.0 | **Production.** Serves every model call. | `AI_PRODUCTION_CONFIG_DECISION.md` |
| **Browser (on-device)** | Gemma 4 E2B via `@litert-lm/core` 0.14.0, OPFS-cached, **self-hosted WASM** | **Ships**, behind an explicit ~2.0 GB download consent gate | commit `cde54fc` |
| **Server-local** | Gemma 4 E2B via Ollama | **Measured and rejected.** `gemma_local.py` is an honest `LocalUnavailable` stub. | `GEMMA_CAPABILITY_MATRIX.md` §9 |

The offline story rides the **browser** tier, not the server-local one. The distinction is
load-bearing and we state it rather than letting "runs on device" blur the two.

Two independent findings closed the server-local tier — it is not an untried option:

1. **Accuracy.** E2B on an RTX 3060 6 GB described the demo octopus photo accurately, then
   identified it as *"a sea lion or seal"* — confident, structured, wrong. 15.9 s cold
   against a 10.1 s hosted median. The artifact was **7.2 GB on disk, not the ~1.3 GB the
   plan assumed**. (§9)
2. **Availability.** A model-list enumeration found **no hosted E2B or E4B on this key at
   all** — exactly two Gemma models, both 26B-class. The edge tier was never reachable
   hosted either. (§6)

---

## The six pillars

Government naming verbatim. `data_kind` is the pillar's own honesty label, rendered on every
response and on every UI surface.

| Pillar | Status | Tier | `data_kind` | Data source |
|---|---|---|---|---|
| **Sustainable Fisheries & Aquaculture** | **live** | hosted + browser | n/a — see note | Open-Meteo Marine; local versioned rules catalogue |
| **Marine Transport & Trade** | implemented, disabled | hosted | **`synthetic`** | aisstream.io — **no regional coverage**, see below |
| **Sustainable Ocean Tourism** | implemented, disabled | hosted | `live` / `cached` / `sample` | Open-Meteo Marine |
| **Ocean-Based Renewable Energy** | implemented, disabled | hosted | `live` / `cached` / `sample` | Open-Meteo Marine |
| **Blue Finance** | declared | hosted | — | user-uploaded documents |
| **Marine Biotechnology** | declared (stretch) | hosted | — | user-uploaded documents |

**"Implemented, disabled" is deliberate.** `PILLARS_ENABLED` defaults to `fisheries`, so
merging a pillar module never silently exposes an endpoint. A disabled pillar answers **503
with an explanation**, which is more honest than a 200 serving data nobody asked for.

**Why fisheries has no `data_kind`.** It predates the pillar contract and was deliberately
*not* rewritten into a module — it works, it is the judged surface, and rewriting it to fit a
newer abstraction would have bought nothing but risk. It is registered as a descriptor so the
listing shows all six, and it carries its own honesty mechanisms (`scope_note` on every ledger
and verification response, MOCK labelling, advisory confidence bands). `DataProvenance` is the
contract for pillars written *after* it.

---

## Measured numbers

Every row is a measurement with a source. No number appears here that does not.

### Hosted inference — production

| | Measured | Source |
|---|---|---|
| End-to-end median | **10 092 ms** (≈69% below the ≈33 s Step-1 baseline) | `AI_PRODUCTION_CONFIG_DECISION.md` §3 |
| Text-only catch logging | 8 296 ms | ibid. |
| Image species analysis | 11 889 ms | ibid. |
| Weather + tool round trip | 14 016 ms | ibid. |
| Structured-output validity | **100%**, enum coercion fired **0 times in 110 requests** | ibid. §1–2 |
| Injection resistance | 100% safety pass across 110 requests | ibid. §3 |

### Species identification — 52 real licensed photos

| | Measured | Source |
|---|---|---|
| Top-1 accuracy | **0.865** | `evaluation/results/species_benchmark.json` |
| Accuracy when the model answered | 0.938 | ibid. |
| **False-confident rate** | **2.1%** | ibid. |
| Morisyen intent accuracy (32-case suite) | 96.9% | `BASELINE_REPORT.md` |

### Model availability — enumerated, one live call, 30 Jul 2026

| | Measured | Source |
|---|---|---|
| Models visible to this key | **56**, of which **2 are Gemma** | `GEMMA_CAPABILITY_MATRIX.md` §6 |
| `gemma-4-26b-a4b-it` / `gemma-4-31b-it` | 262 144 in / 32 768 out, both | ibid. |
| Hosted E2B or E4B | **none exist on this key** | ibid. |
| Largest prompt we actually send | 4 210 characters (species rules) | ibid. §10 |

### Fine-tuning — an adapter that beat production and was rejected anyway

| | v2 adapter | Hosted 26B | Source |
|---|---|---|---|
| Intent accuracy | **85.3%** | 70.6% | `AI_STEP4_FINAL_REPORT.md` |
| Structured validity | 100% | 97.1% | ibid. |
| Median latency | 4.8 s | 18.5 s | ibid. |
| `make_declaration` recall | **1.000** (from 0.455) | — | ibid. |
| **Tool accuracy** | **58.8%** | — | ibid. |

**Gate: REJECTED.** Tool accuracy missed a **70% bar that was committed before training**
(`V2_PRE_REGISTERED_ACCEPTANCE_GATE.md`) and was applied verbatim rather than softened. A
router that picks the right intent and the wrong function executes the wrong thing. Hosted
stays production.

### Platform

| | Measured | Source |
|---|---|---|
| `/health` cold boot, `main` today (all six pillars registered) | **895 ms** median (877–937, 10 runs) | re-measured 30 Jul, `45a728a` |
| `/health` cold boot, before the transport pillar | **852 ms** median (834–905, 10 runs) | PR #16 |
| Backend suite | **413 passed**, 0 network calls in the default tier | 30 Jul, `45a728a` |

Adding the transport pillar cost **+20 ms against 71 ms of run-to-run spread** — smaller
than the noise it was measured in. Readiness never waits on a model or a feed: pillars
register a descriptor at import and load their data on first request.

Both figures are full **process** cold boot — interpreter start and uvicorn import included
— which is what a load balancer waits for. It is not the same quantity as Task 1a's
in-process `<500 ms` readiness figure, and the two should not be compared.

Four tests fail on `main` and are **not** counted above: SHA-256 immutability checks over
archived AI-training evidence, where a recorded digest does not match the committed bytes.
Pre-existing, owned by the AI workstream, unrelated to any pillar. Recorded here because a
suite count that quietly omits its failures is the kind of number this page exists to avoid.

---

## The AIS coverage finding

The Marine Transport pillar was to run on live AIS. It does not, and the reason was measured
rather than assumed — `backend/scripts/ais_coverage_probe.py`, 30 Jul 2026:

| Bounding box | Window | Messages |
|---|---|---|
| Port Louis | 120 s | **0** |
| Mascarene basin | 120 s | **0** |
| Global | < 15 s | **5** |

Key valid, subscription accepted, global stream flowing. **A regional receiver gap — not a
key or service fault.** The third box exists to separate those two explanations; without it,
silence proves nothing.

So the pillar ships on AIS messages **constructed from the documented schema**, labelled
`data_kind: "synthetic"` — not `sample`, which would imply a real capture we do not have.
The live collector is **deliberately unimplemented** rather than half-built: a long-lived
WebSocket is a startup hazard bought for no data. The finding rides in `coverage_note` on
every single response.

---

## What we do not claim

- **The `/verify/:id` ledger proves a record is unaltered since it was logged.** It does not
  prove the underlying catch claim is true. The page says so.
- **Every AI suggestion is advisory**, with a confidence *band* — never a fabricated
  percentage — always with alternatives and a manual path.
- **Every government interaction is labelled MOCK**, including on the receipt.
- **No photos are stored.** Images are analysed in memory and never written to disk. There is
  no GPS beyond a rounded area. So there are no catch thumbnails and no precise positions to
  plot, and we show neither rather than inventing both.
- **Transport ETAs are self-reported by vessels over AIS.** Not port authority data, not a
  validated prediction. Terrestrial AIS is nearshore and incomplete: an empty brief means
  *nothing observed*, never *nothing there*.
- **Transport narrative prose is not yet proven against the live model.** See below.

---

## One finding, opened and closed the same day

**30 Jul 2026 — found.** The inference Protocol's `chat()` hardcoded the fisheries system
instruction, which scopes the model to fisher assistance *and* orders it to always emit
structured output. A live hosted call asking for a Port Louis arrivals brief came back:

> `{"intent": "other", "reply": "I am an analysis engine for fishers, not a port officer.
> I cannot write reports for maritime authorities.", "call": null}`

A hard refusal, wrapped in JSON. Every non-fisheries pillar hit it.

**The nastier half was ours.** The transport pillar's grounding guard checked for invented
vessel identifiers and let that envelope through as `narrative_source: "model"` — a refusal
about to be rendered to a port officer as a brief. That is precisely the failure this
project exists to prevent.

**30 Jul 2026 — resolved.** `chat()` gained an optional `system_instruction`, default `None`
preserving the fisheries path byte-for-byte (decision log 17, PR #20). The guard now rejects
structured output as well as invented identifiers. Both are pinned:

| What | Where |
|---|---|
| The captured refusal, as a regression test | `tests/test_pillar_transport.py::test_narrative_grounding_rejects_the_assistant_envelope` |
| Default-`None` behaviour is unchanged | `tests/test_provider_contract.py::test_chat_default_instruction_is_unchanged` |
| A custom instruction replaces rather than appends | `tests/test_provider_contract.py::test_chat_custom_instruction_reaches_the_provider_call` |

**Still unproven, and we will not pretend otherwise.** The refusal fix is verified against
mocks, not against the live model. **Four live calls to this endpoint have returned a
transient 503, the refusal, a 60 s timeout and a 90 s timeout — no success.** So no capture
of real Gemma prose in the transport narrative exists, and the committed API example shows a
timeout rather than a success.

The refusal mode is fixed and has not recurred. The obvious follow-up hypothesis — that the
brief was simply too long — was **tested and rejected by its own experiment**: cutting it
from two paragraphs to four sentences *and* raising the ceiling to 90 s still timed out
(92.3 s wall), so the bump was reverted as net-harmful. The two cheapest explanations are now
eliminated and the cause is genuinely unexplained. The full matrix, and the one diagnostic
worth running next, are in `GEMMA_CAPABILITY_MATRIX.md` §11.

**None of this touches what a port officer actually reads.** Arrivals, ETAs and congestion
are computed deterministically and were never at risk; the narrative degrades to a mechanical
summary that states why, on every response.

---

## Reproducing the numbers

```bash
cd backend && .venv/bin/python -m pytest tests -q        # offline suite, zero network
.venv/bin/python backend/scripts/ais_coverage_probe.py   # AIS coverage (needs a key)
```

Anything that spends model quota is listed in `GEMMA_CAPABILITY_MATRIX.md` §8 and requires
approval first. That is a project rule, not a formality: the numbers on this page cost real
requests, and each one is recorded where it was spent.
