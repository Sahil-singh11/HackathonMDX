# Remaining Manual Actions — in priority order

## BLOCKING (submission fails without these)

1. **Grant repo access** — the machine's GitHub CLI is authenticated as `YadhavRamsahye`, who currently gets 404 on `Sahil-singh11/HackathonMDX` (not a collaborator). **Sahil**: Settings → Collaborators → add `YadhavRamsahye` with **admin** (admin is needed for the automated visibility flip). Then run: `git push origin main backend-gemma frontend-ux data-training qa-deployment kaggle-presentation`. Until then all 6 commits exist only locally (backed up: `/home/yad/lamer_konekte_backup_20260729_1510.zip` + git bundle).
2. **Make repository PUBLIC before submission** — after pushing: `bash scripts/make_repo_public.sh` (re-runs the release gate, flips visibility, tags `hackathon-submission-v1`, verifies unauthenticated access). If the API refuses, Sahil flips it manually in Settings → Danger Zone.
3. **Submit the Kaggle Writeup** (not draft) — paste `kaggle/writeup.md`, links from `kaggle/project_links.md`. Re-run `scripts/check_writeup_count.py` after any edit.
4. **Upload the demo notebook to Kaggle as PUBLIC** — `kaggle/notebooks/lamer_konekte_demo.ipynb`; attach `GEMINI_API_KEY` as a Kaggle Secret; run all cells once. This is the demo of record if no web URL is deployed.

## HIGH VALUE (directly worth rubric points)

5. **Insert `GEMINI_API_KEY`** into `.env` (copy `.env.example`) → `backend/.venv/bin/python backend/scripts/run_gemma_gates.py` → `evaluation/run_all.py --provider hosted` → update the honesty paragraph in `kaggle/writeup.md` and `docs/BASELINE_REPORT.md` with live results.
6. **Kaggle CLI auth** (`pip install kaggle`, `~/.kaggle/kaggle.json`) → `scripts/kaggle_push_training.sh` → monitor → `evaluate_adapter.ipynb` → fill `training/results/` with real numbers (strict §18E acceptance).
7. **Deploy public URL** — Render account + `deployment/render.yaml` + key as dashboard secret → validate `docs/DEPLOYMENT.md` checklist → update `kaggle/project_links.md`.
8. **Native Morisyen review** — complete `docs/MORISYEN_HUMAN_REVIEW.md`, upgrade name statuses, rebuild frontend.

## OPTIONAL

9. PDF export of the deck (PowerPoint → Export; LibreOffice absent on this machine).
10. Audio recordings (consented) for the audio gate; local E2B edge attempt (needs HF licence acceptance) — only claim if it actually runs.
11. Confirm the official hackathon deadline and correct `docs/TIMEBOX.md` (currently assumed 2026-07-30 13:36 MUT).
