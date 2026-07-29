# Morisyen Review — Step 4 Application Report

Applied 2026-07-29 by `training/scripts/apply_human_review.py`.
Machine-readable record: `training/results/human_review_application.json`.

---

## 1. What was found on disk, before anything was applied

The review sheet `training/data/HUMAN_REVIEW_REQUIRED.csv` was **byte-identical to its
commit `6aa1153`**: all 30 rows `reviewer_status: pending`, zero `corrected_text`, zero
`reviewer_comment`. `docs/MORISYEN_HUMAN_REVIEW.md` (a separate, older register) was also
entirely `_pending_`.

That contradicted the instruction that the review was complete, so it was raised rather
than assumed. The project owner confirmed:

1. **the 30 rows are approved as written, with no wording changes**, and
2. **the approver is not a verified native/fluent Morisyen speaker.**

Both facts are recorded in every artifact below. Nothing was inferred.

## 2. Results

| Metric | Value |
|---|---|
| Total review rows | **30** |
| Approved rows | **30** |
| — of which approved **without any edit** | **30** |
| Corrected rows (wording changed) | **0** |
| Rows with intent changed | **0** |
| Rows with expected tool changed | **0** |
| Unresolved rows | **0** |
| Safety-critical rows reviewed | **8** |
| Reviewer comments containing secrets/private data | **0** |

## 3. Validation performed before applying

The script refuses to write anything if any check fails. All passed:

- every `record_id` resolves to a real dataset record;
- every reviewer `expected_intent` is one of the five allowed intents;
- every reviewer `expected_function` is allow-listed (`ROUTABLE_TOOLS`);
- no reviewer comment or corrected text matches a secret pattern
  (`AIza…`, `hf_…`, `sk-…`, private-key headers, `password`, `api_key`);
- unresolved rows stay `pending` and are never silently upgraded.

## 4. What changed in the dataset

**No Morisyen wording was altered.** Verified by diffing every record against commit
`6aa1153`:

| Field | Records changed |
|---|---|
| `user_input` (the Morisyen text) | **0** |
| `semantic_family` | **0** |
| `split` | **0** |
| `expected_intent` | **0** |
| `expected_tool_call` | **0** |

Only provenance and review metadata moved:

| | Before | After |
|---|---|---|
| `AI_generated_review_required` | 240 | **210** |
| `AI_generated_human_reviewed` | 0 | **30** |
| `human_review_status: pending` | 240 | **210** |
| `human_review_status: reviewed` | 0 | **30** |

Each reviewed record gained a `review` block that keeps the history rather than erasing it:

```json
{
  "reviewed_on": "2026-07-29",
  "reviewer_status": "ok",
  "approver": "project owner (Team Ctrl200)",
  "native_speaker_verified": false,
  "approved_without_edit": true,
  "original_provenance": "AI_generated_review_required"
}
```

Record IDs, semantic families and split membership were preserved exactly, and the three
split files were regenerated from the master so they cannot drift.

Dataset totals unchanged: **240 master · 170 train · 36 validation · 34 internal test**.

## 5. How this may and may not be described

**Permitted:** "30 of 240 records were approved as written by the project owner."

**NOT permitted, and not used anywhere:**

- "native-speaker verified" — the approver is not verified as a native/fluent speaker;
- "corrected by a reviewer" — nothing was corrected;
- "the dataset's Morisyen has been checked line by line" — approval was given as a block,
  with zero edits recorded.

The dataset card, the Kaggle upload and the final handoff all carry the narrower claim.

## 6. Honest caveat

Thirty AI-generated Morisyen strings approved with **zero corrections** is an unusual
outcome. Either the wording genuinely is good, or the review was less granular than a
line-by-line linguistic check. That distinction cannot be settled from the artifacts, so
this report states what is recorded — approval without edits, by a non-verified speaker —
and nothing stronger.

**210 of 240 records (87.5%) remain AI-generated and unreviewed.** That is still the
dataset's largest quality risk and is carried into `docs/AI_FINAL_HANDOFF.md`.
