# Training Dataset Card

This repository holds **two** training datasets with different objectives. Dataset 1 is the
current one for AI Step 3; dataset 2 is retained for provenance.

---

# 1. Lamer Konekte AI Instructions v1 (current)

| | |
|---|---|
| Name | Lamer Konekte AI Instructions v1 |
| Version | 1.0 (2026-07-29) |
| Records | **240** across **116 semantic families** |
| Purpose | Compact-prompt Morisyen **intent recognition and function routing** |
| Not for | Fish-image classification, species identification, legal decisions |
| Built by | `training/scripts/build_ai_instructions_v1.py` (deterministic, re-runnable) |
| Licence | CC-BY-SA-4.0 |
| Frozen prompt | `compact_router_v1`, SHA-256 `44299533f59cc907…` |

## 1.1 Motivation

Step 2 measured intent accuracy at **100% with the full 2 267-char system prompt but 53.8%
with the 1 019-char compact prompt**. The model leans on prompt scaffolding rather than
internalised understanding, and the full prompt is the largest fixed cost per request. This
dataset exists to close that specific gap.

Explicitly *not* in scope: JSON/enum formatting. Step 2 measured 100% exact enum validity
and 0 coercions across 110 requests, so training that would be solving a solved problem.

## 1.2 Composition

| Group | Records | Content |
|---|---|---|
| A — Morisyen intent | 61 | the five intents in natural Morisyen |
| B — Function selection | 48 | all eleven routable tools, plus "no tool" cases |
| C — Function arguments | 32 | location, forecast day, count, species/analysis id, missing, invalid, ambiguous, out-of-range |
| D — Mixed language | 25 | Morisyen+French, Morisyen+English, informal spelling, fragments |
| E — Uncertainty / missing info | 28 | unknown species, no measurement, unclear intent, contradictions, wrong photo |
| F — Safety and refusal | 30 | safety guarantees, invented law, bypass confirmation, visual size, unknown function, injection, secrets, fake ministry, privacy, pressure |
| G — English controls | 16 | regression guard |

**By intent:** identify_catch 61 · other 55 · weather_query 50 · log_catch 49 ·
make_declaration 25.
**By language:** mfe 208 · en 18 · mfe-en 8 · mfe-fr 6.

**Safety categories (32 records):** marine_safety_guarantee 6 · invented_regulation 6 ·
prompt_injection 4 · bypass_confirmation 2 · visual_size_as_measurement 2 ·
unknown_function_request 2 · secret_request 2 · fake_official_submission 2 ·
legal_decision_request 2 · false_certainty_pressure 2 · privacy_request 2.

## 1.3 Splits — assigned by semantic family

| Split | Records | Share |
|---|---|---|
| train | 170 | 70.8% |
| validation | 36 | 15.0% |
| internal test | 34 | 14.2% |
| **external test** | **32** | immutable, never trained on |

A *semantic family* is one underlying user need; its variants are paraphrases of it. Splits
are assigned **per family** via a deterministic hash, so two paraphrases of one seed can
never land on opposite sides of a boundary and inflate the held-out score.
`scripts/check_semantic_family_split.py` proves zero families straddle splits.

## 1.4 External test set — immutable

`evaluation/cases/morisyen_cases.json` (32 cases) is marked `immutable_external_test` and
checksummed in `training/data/external_test_manifest.json`
(SHA-256 `966c54640cde7d4d…`, plus a per-case hash).

Rules, enforced by `scripts/check_training_leakage.py`: never train on these cases, never
paraphrase them into training data, never copy their exact wording, never use their
expected answers as templates.

The checker rejects any training record that is an exact copy, ≥0.80 similar, **or shares a
four-word run** with a benchmark case. During authoring it caught 8 real overlaps
(e.g. `"met sa dan mo"`, `"ek donn mwa enn"`) and 4 cross-split near-duplicates. All were
fixed **in the data**, never by relaxing a threshold.

## 1.5 Record schema

`id`, `language`, `task`, `semantic_family`, `provenance`, `human_review_status`,
`system_prompt_version`, `compact_prompt_version`, `user_input`, `available_tools`,
`expected_intent`, `expected_tool_call`, `expected_arguments`,
`expected_structured_output`, `expected_final_behaviour`, `forbidden_behaviour`,
`safety_category`, `source_ids`, `split`, `group`.

`expected_structured_output` always pins `species_confirmation_required: true` and
`measured_size_required: true` — the dataset never teaches a lowerable invariant.

## 1.6 Provenance and review status — read before quoting quality

| Provenance | Records | | Review status | Records |
|---|---|---|---|---|
| `AI_generated_review_required` | **192** | | `pending` | **192** |
| `team_authored` | 48 | | `not_required` | 48 |

**The Morisyen in this dataset is largely AI-generated and has not been verified by a
native speaker.** It is not described as native-speaker verified anywhere. The 30
highest-impact records are queued in `training/data/HUMAN_REVIEW_REQUIRED.csv`; see
[MORISYEN_DATA_REVIEW_GUIDE.md](MORISYEN_DATA_REVIEW_GUIDE.md).

Evaluation reports **reviewed and unreviewed subsets separately**
(`reviewed_subset_accuracy` / `unreviewed_subset_accuracy`) so an unreviewed record cannot
silently inflate a headline number.

## 1.7 Validation

| Check | Script | Result |
|---|---|---|
| Schema, ids, enums, secrets, duplicates | `validate_training_dataset.py` | PASS |
| External-test immutability + cross-split near-duplicates | `check_training_leakage.py` | PASS |
| Semantic-family split integrity | `check_semantic_family_split.py` | PASS |
| Tool names + arguments vs the live backend registry | `check_tool_arguments.py` | PASS |
| No unsafe training target | `check_training_safety.py` | PASS |

Reports land in `training/results/`. **A full training run must not begin when the leakage
check fails**, and the Kaggle notebook re-runs the family and near-duplicate guards
in-session before training.

## 1.8 Known limitations

1. **Small** — 240 records over 116 families. Enough to test the hypothesis, not a
   production-grade router.
2. **Mostly unreviewed Morisyen** (192/240) — the dominant quality risk.
3. **Synthetic user inputs.** No real fisher messages; no consent flow exists for that yet.
4. **Intent distribution is not natural** — `make_declaration` is deliberately
   over-weighted so the rarest intent has enough support.
5. **No audio, no images** — a text-routing dataset by design.
6. **Shallow argument coverage** for rare tools (`queue_for_offline_sync`,
   `get_current_demo_date` have 2 records each).

## 1.9 Files

```
training/data/master_records.jsonl        240 records, source of truth
training/data/train.jsonl                 170
training/data/validation.jsonl             36
training/data/test.jsonl                   34
training/data/external_test_manifest.json  checksums for the immutable benchmark
training/data/dataset_statistics.json      the counts quoted above
training/data/HUMAN_REVIEW_REQUIRED.csv    30-record review queue
training/configs/compact_router_v1.json    frozen prompt + SHA-256
```

---

# 2. Legacy dataset (72 records, superseded)

Built by `training/scripts/build_training_data.py`. **Not used for AI Step 3** — its
objective is different (image identification), and it has no `semantic_family`,
`provenance` or `human_review_status` fields. Retained for provenance and because the
image-identification records may seed future multimodal work.

## Record types
1. **image_identification** — licensed manifest images; instruction to suggest ONLY from the candidate list with uncertainty; expected constrained JSON (species, confidence, characteristics, `confirm_species` next step). Split inherited from the image manifest (observation-level split → no image leakage).
2. **text_intent** — Morisyen/English instructions with expected intent and expected allow-listed function call. Paraphrase families are split as whole families (template de-dup: all paraphrases of one family land in one split).
3. **safety** — expected safe responses: refuse legality decisions, refuse invented rules, refuse navigation guarantees, resist prompt injection.

## Leakage controls
- Image splits follow `sha256(observation_id)` from the manifest (no augmented copy can cross splits because variants inherit the parent row's split).
- Text template families hashed as a unit.
- pytest: `backend/tests/test_dataset_leakage.py`.

## Honesty
Expected outputs are heuristic supervision written by the team, not gold biological annotation; species labels come from research-grade iNaturalist community IDs.
