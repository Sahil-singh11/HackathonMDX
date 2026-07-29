# Dataset Card — Lamer Konekte AI Instructions v2

| | |
|---|---|
| Name | Lamer Konekte AI Instructions v2 |
| Version | 2.0 (2026-07-29) |
| Records | **338** across **164 semantic families** |
| Built from | reviewed v1 (240) + **98 new targeted records** |
| Purpose | Compact-prompt Morisyen **intent recognition and function routing** |
| Built by | `training/scripts/build_ai_instructions_v2.py` (deterministic, re-runnable) |
| Frozen prompt | `compact_router_v1`, SHA-256 `44299533f59cc907…` (unchanged from v1) |
| Licence | CC-BY-SA-4.0 |

v1 remains frozen and verifiable at `training/archive/v1/`.

---

## 1. Why v2 exists

v2 is a **targeted** revision, not a bigger v1. Every addition traces to a measured v1
failure (`docs/V1_TARGETED_ERROR_ANALYSIS.md`):

| v1 finding | v2 response |
|---|---|
| `make_declaration` recall **0.455**, precision 1.000; 6 of 11 missed, **4 leaking to `log_catch`**, zero over-predicted | declaration records **25 → 79** |
| Declaration ↔ logging is the specific boundary | **16 explicit contrast records** |
| Tool accuracy 58.8%; **5 correct-intent-wrong-tool**; rare tools at 2 records each | **24 argument records** |
| Mixed-language and English **unmeasured** on the internal test | **10 natural/mixed records** + mixed-language declarations in the challenge set |
| Safety was 100% — must not regress | **16 safety/negative controls** |

## 2. Composition

| Group | New in v2 | Content |
|---|---|---|
| A2 — Declaration routing | 32 | today, weekly, monthly, preview, correct, selected catches, missing catches, missing date, natural Morisyen, mfe-fr, mfe-en, prepare-not-submit, submit-mock, official-request refusal, declaration-before-logging |
| B2 — Logging ↔ declaration contrasts | 16 | one catch, many catches, show recent, declare from recent, summary, add-then-prepare, edit catch, submit-vs-record |
| C2 — Function arguments | 24 | catch ids, selected lists, period dates, forecast day, limits, unsupported dates, invalid counts, ambiguous places, consent, no-consent, species ids, offline payload |
| D2 — Natural / mixed Morisyen | 10 | casual register, mfe-fr, mfe-en, fragments |
| E2 — Safety and negative controls | 16 | fake ministry, bypass confirmation, invented rule, safety guarantee, unrestricted tool, injection, secret extraction, visual-size legal claim |

**Totals by intent (338):** make_declaration 79 · log_catch 69 · identify_catch 67 ·
other 63 · weather_query 60.
**By language:** mfe 298 · en 18 · mfe-en 12 · mfe-fr 10.
**By declaration tool:** `prepare_catch_declaration` 49 · `submit_mock_declaration` 14.

## 3. THREE separate test sets — never merged

| Set | Records | File | Status |
|---|---|---|---|
| Original internal test | **34** | `internal_test_v1_34.jsonl` | v1 membership, **34/34 verified intact, 0 moved**; pinned to its own file because `test.jsonl` grew to 48 in v2 and would not be comparable |
| Immutable external benchmark | **32** | `evaluation/cases/morisyen_cases.json` | never trained on, never paraphrased, checksum-verified |
| **v2 challenge set** | **24** | `v2_challenge_test.jsonl` | **frozen and committed before training**, 24 families appearing nowhere in train/validation/test |

**One record on the 34-record internal test is ≈ 2.94 pp.** No conclusion may rest on a
one-record difference.

### Challenge-set coverage

declaration↔log confusion · prepare vs submit · hard arguments (location+day, counts,
month-to-date) · mixed-language declarations (mfe-en, mfe-fr) · missing information ·
ambiguity · unsafe requests (legal claim in a document, sea-safety certification) ·
prompt injection · multi-step requests · declaration-recall probes.

By intent: make_declaration 11 · other 5 · log_catch 4 · identify_catch 2 ·
weather_query 2.
SHA-256 `23327eae5f7e8ef0…`, recorded in `v2_challenge_manifest.json` and
`v2_challenge_checksums.sha256`.

## 4. Splits

| Split | Records |
|---|---|
| train | 248 |
| validation | 42 |
| test (grown) | 48 — **evaluation uses the pinned 34 only** |

New families were assigned to splits **before** variants were generated, using a
deterministic hash. Every v1 record keeps its original id, family and split.

## 5. Provenance and review — read before quoting quality

| Provenance | Records |
|---|---|
| `AI_generated_review_required` | **308** |
| `AI_generated_human_reviewed` | **30** |

The 30 reviewed records were **approved as written by the project owner on 2026-07-29 with
zero corrections**. Each carries a `review` block with
`native_speaker_verified: false`.

**This dataset is NOT native-speaker verified.** Permitted phrasing: "30 of 338 records
were approved as written by the project owner." Not permitted: "native-speaker verified",
"corrected by a reviewer", "checked line by line".

**308 of 338 records (91%) remain AI-generated and unreviewed.** That is the dataset's
largest quality risk.

## 6. Validation — all gates pass

`scripts/validate_v2_dataset.py`:

| Check | Result |
|---|---|
| Schema, ids, enums, secrets, duplicates | **PASS** |
| Leakage (external + challenge + cross-split) | **PASS** |
| Semantic-family integrity | **PASS** |
| Tool arguments vs the live registry | **PASS** |
| Safety targets | **PASS** |

Reports: `training/results/v2_dataset_validation.json`, `v2_leakage_report.json`,
`v2_semantic_split_report.json`, `v2_argument_validation.json`,
`v2_safety_validation.json`.

The leakage checker again earned its keep: three **new** v2 records overlapped the external
benchmark (two ≈0.80 similar to `mfe-08`/`mfe-22`, one sharing a four-word run with
`mfe-17`). All three were rewritten **in the data**; no threshold was touched.

## 7. Known limitations

1. **Still small.** 338 records over 164 families.
2. **91% unreviewed Morisyen** — the dominant risk.
3. **Synthetic inputs.** No real fisher messages; no consent flow exists yet.
4. **Deliberately unbalanced.** `make_declaration` is now the largest intent (79) because
   it was the measured failure — this does **not** reflect real traffic.
5. **The 34-record internal test is small** — 2.94 pp per record.
6. **New records inherit v1's authoring style**, so they may share blind spots with it.

## 8. Files

```
training/data/master_records_v2.jsonl      338 records, source of truth
training/data/train.jsonl                  248
training/data/validation.jsonl              42
training/data/test.jsonl                    48 (grown; NOT the evaluation set)
training/data/internal_test_v1_34.jsonl     34 pinned evaluation set
training/data/v2_challenge_test.jsonl       24 frozen challenge set
training/data/v2_challenge_manifest.json    challenge checksums + coverage
training/data/dataset_statistics_v2.json    the counts above
training/archive/v1/                        frozen v1 snapshot
```
