# Writeup handout — for Yadhav (and the Claude web session continuing it)

**Written 2026-07-30. Author: Sahil's session (frontend + pillar integration lane).**

This is a delta handout. It does **not** replace `kaggle/writeup.md` — that writeup is
good and mostly still true. This tells you exactly what has changed underneath it,
what is now false, and what is missing, with the evidence for each claim.

---

## 0. Read this first — the two hard constraints

**1. The writeup is at the word limit.** `kaggle/writeup.md` is **1,489 words against a
1,500 limit** (`kaggle/writeup_word_count.txt`). Every sentence you add must displace
one. Section 4 below suggests specific cuts with word estimates. Do not silently blow
the limit.

**2. The writeup currently describes a different, smaller product than the one that
exists.** It describes the fisheries catch-recording app only. The word "pillar" appears
exactly once in it — line 5, as the *track label* `**Pillar:** Blue Economy` — and the
**six implemented blue-economy pillars are never mentioned at all**, though they are now
five-sixths of the running application and the bulk of two days' work. That is the
single biggest gap.

---

## 1. What the app actually is now

`GET /api/pillars` on a running instance, today:

| Pillar | Status | What it does |
|---|---|---|
| Sustainable Fisheries & Aquaculture | **live** | The original catch flow. Already in the writeup. |
| Marine Transport & Trade | **live** | Live Open-Meteo sea state at the Port Louis approach → transit windows for two craft classes, from fixed published thresholds. |
| Sustainable Ocean Tourism | **live** | Beach/lagoon suitability per site per activity (swimming, snorkelling, diving, windsurfing, kitesurfing), from fixed thresholds anchored to the WMO sea-state scale. |
| Ocean-Based Renewable Energy | **live** | Wave and wind power density at five candidate offshore sites, computed in Python from public forecast values. |
| Blue Finance | **live** | Checks an uploaded blue-bond / ESG document against blue-finance criteria. Advisory, read-only. |
| Marine Biotechnology | registered, **not built** | Declared with its data sources; the page says "Not part of this build." Do not claim it. |

The government's own pillar naming is used verbatim throughout.

---

## 2. NEW material for the writeup, with evidence

Everything here is measured, not estimated. File paths are given so you can verify any
claim before writing it.

### 2.1 The pillar architecture (the biggest omission)

A `PillarModule` protocol (`backend/app/pillars/base.py`) with a mandatory
`DataProvenance` block on **every** result (`provenance.py`): source name, source URL,
retrieval time, `data_kind` ∈ `live | cached | sample | synthetic`, which model was
involved, and a `coverage_note` saying what the data does **not** cover. A pillar is
only served when it is both implemented *and* enabled in settings, so merging a module
never silently exposes it (`registry.py`).

The division of labour is the same in all five live pillars and is the thing worth
writing about: **every number is computed deterministically in Python and unit-tested;
the model only ever writes prose *about* numbers it was given.** Model output is never
parsed back into data.

### 2.2 Three defences that stop the model inventing things

These are strong, demonstrable engineering-discipline material — arguably better
writeup content than anything currently in §"Native function calling".

**(a) The refusal-envelope guard** — `backend/app/pillars/narrative.py`

A real bug we found on screen and fixed. `chat()` injects the fisheries catch-assistant
system instruction unless a caller overrides it, so asking it an ocean-energy question
produced a *refusal wrapped in the fisheries JSON envelope*, which then rendered
verbatim on the page as the site's "Analyst note", fences and `intent` field included:

```
```json
{"intent":"other","reply":"I am sorry, I can only help with identifying and
 logging fish catches. I cannot assist with ocean-energy analysis.","call":null}
```
```

Root cause: `backend/app/prompts/system.py:10`. Fixed two ways — a per-pillar scoped
`system_instruction`, and `salvage_reply()` as a second line of defence, which parses
the envelope, takes the reply for the active language, and returns empty for a refusal.
`intent` and `call` are never read. Proven with a single-variable test against the live
model: scoped instruction → no refusal; default instruction → the envelope above.

**(b) The number firewall** — `backend/app/pillars/numeric_guard.py` (Shirish)

Extracts every number a narrative states — digits *and* cardinal words — and rejects
any that cannot be traced back to the figures the model was actually given, within a
documented rounding tolerance. Honest about its limits in its own docstring: it cannot
judge whether a *qualitative* framing of a grounded number is fair, and it is not a
units checker.

Two demonstrations worth quoting:
- It rejects the existing `_LyingProvider` test fixture's fabricated "9999 kW/m"
  outright. Previously that lie survived into the prose (it was only ever kept out of
  the computed figures).
- **It caught a fabricated number in our own test data.** The transport "grounded
  output" fixture asserted on prose reading "Five vessels report Port Louis" while the
  fixture holds a different count. The guard failed the test. The fixture was wrong,
  not the guard.

**(c) Honest attribution of who wrote each sentence**

Every narrative records which rung produced it: `model` (fresh call), `cached` (the same
already-grounded prose reused), `deterministic_fallback` (assembled in code from the
computed figures), or `none`. The UI renders model-written and mechanically-assembled
prose as visibly different things — a badge plus a sentence saying "No model reasoned
over these figures". A fallback dressed up as model output would be the exact overclaim
the project's rules exist to prevent.

### 2.3 The narrative cache and `DEMO_MODE` — the demo-reliability story

`backend/app/pillars/narrative_cache.py` (Shirish). Persists grounded model prose to
SQLite keyed on `(pillar, rounded input figures, language, provider)`. Only text that
already passed every guard is ever stored.

**Measured on this machine, and the honest version of this story has two halves:**

| Endpoint | Normal | `DEMO_MODE=true` |
|---|---|---|
| `energy/resource` | 61 s | **0.018 s** |
| `tourism/brief` | 72 s | **0.015 s** |
| `transport/approach` | 34–102 s | **3.1 s** |

The half that matters for honesty: **the cache alone does not fix the latency.** The
hosted model mostly times out against the 60 s ceiling, and a timeout produces no prose
to cache — only 1 of 5 energy sites ever became `cached` across repeated calls.
`DEMO_MODE=true` skips the model entirely and serves cache-or-mechanical, and the output
stays honest (one site real cached prose, four labelled mechanical, no blanks). If you
write a latency number, write the `DEMO_MODE` one and say what it means.

### 2.4 Maps: one shared Leaflet chart, real coastline, no tile server

`frontend/src/components/map/ChartMap.tsx` + `geometry.ts` (Dhanesh's consolidation,
coastline and fixes from this lane).

- **No tile layer anywhere.** A tile is a network request per tile, and this app's
  premise is that it works with no signal — the fetch fails exactly when someone needs
  the app. The basemap is GeoJSON shipped in the bundle. It cannot go blank offline.
- **The coastline is real.** OpenStreetMap `natural=coastline` for the main island: 200
  way fragments, 24,473 nodes, chained into one closed ring and Douglas-Peucker
  simplified to **1,058 points**. It replaced a 66-point hand-traced outline that
  rendered Mauritius as a rounded blob — 66 points cannot hold a bay, so Grand Baie,
  Baie du Tombeau, the Mahebourg notch and the Le Morne peninsula were all smoothed
  away.
- **Verified, not assumed.** Bounding box lon 57.3084–57.8085, lat −20.5255 to −19.9816.
  Nearest coastline point to five known landmarks, in km: Cap Malheureux 0.0, Le Morne
  0.3, Mahebourg 0.1, Souillac 0.1, Port Louis 0.0.
- **ODbL-1.0 attribution is a licence condition**, shown in the map's attribution
  control and in prose. Do not describe the basemap without crediting OpenStreetMap.
- Bundle: the map chunk went **957 kB (MapLibre) → 177 kB (Leaflet + coastline)**,
  lazy-loaded.
- Accessibility: **a map is never the only route to the data.** Every marker is also a
  keyboard-navigable button in a side list with the same label and action, and in the
  Sunlight theme the map is not drawn at all — the list stands alone.

### 2.5 AIS: a physics limit, reported rather than papered over

Terrestrial AIS needs a receiver within roughly 40 nm and **none covers Mauritius**
(satellite AIS does, but it is a paid product). We probed the live aisstream feed on
30 Jul 2026: global stream flowing, **zero messages for the Mauritius region**.

So the transport pillar **leads with the live sea state**, which is genuinely live, and
the vessel arrivals are a clearly-labelled demonstration feed: `data_kind: synthetic`,
rendered under a loud badge reading "Generated data — not an observation of anything.
Do not read these as real conditions", with the coverage note verbatim. Vessels are
drawn at their **true range** along **one schematic bearing**, on a dashed construction
line, with the caveat in HTML beside the map — because AIS reports a distance, not a
bearing, and drawing a bearing we do not have would be inventing data.

### 2.6 Design system work (only if you have words spare — lowest priority)

A shared pillar page framework (`frontend/src/components/pillar/`) with a fixed section
order — answer → figures → visual → detail → method → limits — so every pillar leads
with a plain-language conclusion instead of making the reader derive it from a table.

Six per-pillar accent hues derived from **semantic tokens only** (no hex literals), so
they follow every theme repoint. Two findings are the interesting part: deriving the
biotech violet under **night vision** produces `#00BEE0`, a bright cyan, in the one
theme built to emit no blue light so a fisher's dark adaptation survives; in
**Sunlight** the same recipe lands on olive and collides with the finance green. Both
themes therefore collapse to a single accent by design. 24 contrast checks across four
theme states pass: accent rules ≥ 3.94:1, body text ≥ 9.81:1.

---

## 3. STALE — claims in the writeup that are now wrong

Fix these regardless of whether you add anything.

| Line | Current text | Correct as of 2026-07-30 |
|---|---|---|
| §Safety and limitations (line 43) | "**44 backend tests** enforce these invariants" | **583 passing.** Say "583 backend tests". (12 fail locally — 9 from a developer `.env` override of `PILLARS_ENABLED`, 3 needing adapter artefacts not downloaded on that machine. Neither is a product defect; do not mention them, just don't cite a failing count.) |
| §Impact and deployment (line 51) | "The repository is public" | Verify before submitting. It is `https://github.com/Sahil-singh11/HackathonMDX` and pushes now work — the "push → 404" blocker in `docs/FINAL_SUBMISSION_REPORT.md` is resolved. |
| Whole document | Describes one pillar | Five pillars are live. See §1. |

`docs/FINAL_SUBMISSION_REPORT.md` is from **2026-07-29 15:15** and is broadly stale now
(it still records the API key and Kaggle auth as blocking, and 44 tests). Do not copy
numbers out of it.

---

## 4. Where the words can come from

The writeup has 11 words of headroom. Suggested displacements, in order of what I would
cut first:

1. **§Sprint challenges (line 47, ~85 words).** Cut to one sentence or drop entirely.
   The credential blockers it describes are largely resolved, so it now reads as an
   excuse for problems that no longer exist. **Biggest, cheapest win.**
2. **§Dataset, training and evaluation (line 33, ~200 words).** The dataset provenance
   detail (SHA-256, per-file attribution, observation-level splits) is excellent but
   long. The *rejected adapter* story must stay — it is the strongest
   engineering-discipline paragraph in the document. Trim the dataset mechanics, keep
   the gate decision. Recoverable: ~50–60 words.
3. **§Native function calling (line 29, ~110 words).** The twelve-function list can be
   compressed to a count plus two examples. Recoverable: ~30 words.
4. **§Architecture (line 25, ~115 words).** The pipeline arrow-chain can lose two
   stages without losing meaning. Recoverable: ~20 words.

That is roughly **180–200 words** — enough for a solid pillar paragraph plus the stale
fixes.

**If you can only add one thing, add this:** a paragraph saying the app is now six
government blue-economy pillars, five live, each carrying a mandatory provenance block
declaring source, retrieval time, whether the data is live/cached/synthetic, and what it
does not cover — and that every figure is computed in Python while the model only writes
prose about figures it was given, with a firewall that rejects any narrative citing a
number it was not.

---

## 5. Do NOT claim — honesty guardrails

The project's credibility rests on these. Every one has been enforced in code and
several were fought for.

- **Do not claim the fine-tuned adapter is in use.** It is not. Live readiness:
  `available: False`, `adapter_path: None`. Provider modes are `{hosted, local, mock}`
  and a test asserts no mode may contain `finetuned`/`adapter`/`e2b`; the router raises
  `RouterUnavailable`. Production is hosted `gemma-4-26b-a4b-it`. The writeup's existing
  account of this (trained, 58.8% tool selection, below the pre-committed gate,
  rejected) is **correct — keep it exactly as it is.**
- **Do not present the AIS vessel arrivals as real traffic.** They are a labelled
  demonstration feed. See §2.5.
- **Do not claim Marine Biotechnology.** Registered, not built.
- **Do not claim a reef, bathymetry or depth layer.** We have no licensed source; the
  map says "not for navigation" and draws none.
- **Do not claim catch photo storage or precise GPS.** Photos are analysed in memory and
  never written to disk; coordinates are rounded to ~2 dp everywhere.
- **Do not quote a fabricated confidence percentage.** The API returns a band
  (low/moderate/high), never a number.
- **Do not describe `/declaration` as a real filing.** It is labelled MOCK, including on
  the receipt.
- **Do not overclaim `/verify/:id`.** It proves a record is unaltered since it was
  logged. It cannot prove the underlying claim is true, and the page says so.

---

## 6. Known open items (context, not writeup content)

- `frontend/src/pages/CatchFlow.tsx` imports `AssistantBot` and never renders it. The
  import was removed to unblock `npm run build` (`noUnusedLocals` was failing `main`
  for everyone; dev mode does not typecheck, so it went unnoticed). **The bot is
  currently dead code and needs mounting by whoever built it.**
- `DEMO_MODE=true` is not set in the repo `.env`. For a live demo it should be — see
  §2.3 for the numbers.
- Two pillar page frameworks briefly coexisted; the team kept Dhanesh's and the
  per-pillar accents were ported onto it. Nothing outstanding.

---

## 7. Verify anything here in one command

```bash
# pillar status, provenance and coverage notes
curl -s http://127.0.0.1:8000/api/pillars | python -m json.tool

# backend suite (expect 583 passed)
cd backend && .venv/Scripts/python -m pytest tests -q \
  --deselect tests/test_hosted_integration.py

# which model is actually serving
curl -s http://127.0.0.1:8000/api/config/public | python -m json.tool

# fine-tuned adapter readiness (expect available: False)
cd backend && .venv/Scripts/python -c \
  "from app.providers import finetuned_router as f; print(f.readiness().as_dict())"
```

Run the app: `scripts/start.sh` (dev mode by default), then `http://127.0.0.1:5173`.
