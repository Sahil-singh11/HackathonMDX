# Morisyen Data Review Guide

For the native/fluent Morisyen speaker reviewing `training/data/HUMAN_REVIEW_REQUIRED.csv`.

**Time needed:** ~30–45 minutes for the 30 queued records.

---

## 1. Why you are being asked

Most Morisyen text in *Lamer Konekte AI Instructions v1* is **AI-generated and not yet
verified by a native speaker**. It is labelled `AI_generated_review_required` in the
dataset and is never described as native-speaker verified anywhere in our documentation
or writeup.

Your review converts records to `AI_generated_human_reviewed`. Final metrics report
reviewed and unreviewed subsets **separately**, so an unreviewed record never silently
inflates a quality claim.

## 2. What is in the queue

The 30 highest-impact records, prioritised by:

1. safety warnings (refusals, guarantees, invented-law requests),
2. weather requests,
3. declaration requests,
4. ambiguous Morisyen,
5. mixed-language inputs (Morisyen + French / English),
6. informal spelling variants,
7. function arguments,
8. octopus-closure style questions.

## 3. How to review

Open `training/data/HUMAN_REVIEW_REQUIRED.csv` in a spreadsheet. For each row:

| Column | What to do |
|---|---|
| `record_id` | Do not change |
| `original_text` | The Morisyen a fisher supposedly typed |
| `intended_meaning` | What the assistant is expected to do — check this matches the text |
| `expected_intent` | One of the five intents; correct it if the text really means something else |
| `expected_function` | The tool that should be selected (may be empty) |
| `reviewer_status` | Set to `ok`, `reworded`, or `wrong_label` |
| `reviewer_comment` | Why, briefly — especially for `wrong_label` |
| `corrected_text` | Only if you changed the wording |

### The three judgements

**A. Is this how a Mauritian fisher would actually write it?**
Not "is it grammatical Morisyen" — is it *plausible*. Fishers type quickly, drop accents,
mix in French and English, and abbreviate. Awkward-but-real beats polished-but-artificial.
If it reads like a translation exercise, reword it.

**B. Is the labelled intent right?**
Read only `original_text`, decide the intent yourself, then compare. If they disagree, the
label is probably wrong — set `wrong_label` and put the right one in `expected_intent`.

**C. Is the expected behaviour safe?**
For safety rows especially: the assistant must never state a fisheries rule, never say a
catch is legal or illegal, never guarantee the sea is safe, never skip species
confirmation, never treat a photo-judged size as a measurement, never reveal
configuration, and never call the declaration endpoint official. If `intended_meaning`
implies otherwise, flag it — that is a defect in our data, not in your reading.

## 4. Please do NOT

- **Do not** copy wording from `evaluation/cases/morisyen_cases.json`. Those 32 cases are
  immutable external test data. Reusing their phrasing contaminates the benchmark, and
  `scripts/check_training_leakage.py` will reject the dataset (shared four-word runs are
  enough to trip it).
- **Do not** make every record grammatically perfect. Informal spelling and fragments are
  deliberate coverage.
- **Do not** add new records here — this file is a review queue, not an authoring file.

## 5. After review

```bash
# 1. apply the reviewed CSV back into the dataset
python training/scripts/apply_human_review.py      # to be added when the CSV comes back

# 2. re-run every validator (leakage MUST pass)
python scripts/validate_training_dataset.py
python scripts/check_training_leakage.py
python scripts/check_semantic_family_split.py
python scripts/check_tool_arguments.py
python scripts/check_training_safety.py

# 3. push a new dataset version and re-run training
pwsh scripts/kaggle_push_ai_dataset.ps1 -NewVersion -Message "human review batch 1"
pwsh scripts/kaggle_resume_ai_training.ps1
```

If you reword text, the leakage check must be re-run before any training — it is the gate
that protects the benchmark.

## 6. Current status

| | Count |
|---|---|
| Total records | 240 |
| `team_authored` (review not required) | 48 |
| `AI_generated_review_required` (pending) | 192 |
| Queued for review now | 30 |
| Safety-category records | 32 |

The remaining 162 pending records stay marked as unreviewed until someone reviews them.
That label is the honest one and should not be changed without an actual review.
