# Remaining Manual Actions — in priority order

## DONE ✅

1. ~~Grant repo access~~ — **DONE 29 Jul ~15:35**: machine re-authenticated as `YedTorma` (push access, **no admin**); all branches pushed and in sync.
5. ~~Insert `GEMINI_API_KEY` + run gates~~ — **DONE 29 Jul ~16:20**: all ten gates PASS on real inference (`docs/GEMMA_GATES.md`); live app verified (octopus photo → correct suggestion; Morisyen weather → `get_marine_conditions` round trip); hosted evaluation run recorded in `evaluation/results/baseline.json`; writeup updated.

## BLOCKING (submission fails without these)

2. **Make repository PUBLIC before submission** — `bash scripts/make_repo_public.sh` (re-runs the release gate, flips visibility, tags `hackathon-submission-v1`). ⚠️ `YedTorma` has **push but not admin** — the API flip will be refused, so **Sahil** must either grant YedTorma admin or flip it manually: Settings → General → Danger Zone → Change visibility → Public, then we push the tag.
3. **Submit the Kaggle Writeup** (not draft) — paste `kaggle/writeup.md`, links from `kaggle/project_links.md`. Re-run `scripts/check_writeup_count.py` after any edit.
4. ~~Kaggle demo notebook~~ — **DONE 29 Jul ~19:10.**
   https://www.kaggle.com/code/yuvineappadu/lamer-konekte-gemma-4-demo-team-ctrl200 — PUBLIC (verified 200 logged
   out), version 7 `COMPLETE`, independently verified from the published log: hosted mode on
   `gemma-4-26b-a4b-it`, real licensed hero photo, `octopus_cyanea` at **high** confidence,
   `real_inference: true`, closed-season comparison correct, and zero key material in the output.
   ⚠️ Do NOT push this notebook via the Kaggle CLI again — it detaches the secret (see `kaggle/README.md`).

## HIGH VALUE (directly worth rubric points)

6. **Kaggle CLI auth** (`pip install kaggle`, `~/.kaggle/kaggle.json`) → `scripts/kaggle_push_training.sh` → monitor → `evaluate_adapter.ipynb` → fill `training/results/` with real numbers (strict §18E acceptance). Owner: Dhanesh.
7. ~~Deploy public URL~~ — **DONE 29 Jul ~17:20**: **https://lamer-konekte.onrender.com** live on Render (Frankfurt, free tier). All 9 validation checks passed incl. real hosted inference through the public URL and zero key material in the served bundle. Auto-deploys on push to `main`; switch to manual deploys before the jury demo to freeze a known-good build.
8. **Native Morisyen review** — complete `docs/MORISYEN_HUMAN_REVIEW.md`, upgrade name statuses, rebuild frontend. Owner: any native speaker on the team.

## OPTIONAL

9. PDF export of the deck (PowerPoint → Export; LibreOffice absent on this machine).
10. Audio recordings (consented) for the audio gate; local E2B edge attempt (needs HF licence acceptance) — only claim if it actually runs.
11. Confirm the official hackathon deadline and correct `docs/TIMEBOX.md` (currently assumed 2026-07-30 13:36 MUT).
