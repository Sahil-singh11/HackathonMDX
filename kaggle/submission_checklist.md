# Kaggle Submission Checklist — Lamer Konekte

## Before freeze (2026-07-30 10:36 MUT assumed)
- [x] Writeup drafted ≤1,500 words (currently 1,282 — `scripts/check_writeup_count.py`)
- [x] 6 Kaggle notebooks valid JSON; demo notebook runs top-to-bottom in mock mode
- [x] Backend tests green (44), frontend production build green
- [x] Evaluation results committed and honestly labelled
- [ ] **Insert `GEMINI_API_KEY` into `.env`** → run `backend/scripts/run_gemma_gates.py` → update the "Honesty note" paragraph in `writeup.md` with live gate results → re-run word count
- [ ] Authenticate Kaggle CLI → `scripts/kaggle_push_training.sh` → record training outcome (or leave the documented blocker paragraph as-is)
- [ ] Deploy public URL (or confirm Kaggle notebook as the demo of record) → update `project_links.md`
- [ ] Native-speaker pass on `docs/MORISYEN_HUMAN_REVIEW.md` critical strings

## Final verification (2026-07-30 12:36 MUT assumed)
- [ ] `scripts/release_gate.sh` passes (secret/licence/large-file/media scans, tests, build)
- [ ] Repository flipped PUBLIC and loads without login; tag `hackathon-submission-v1` pushed
- [ ] `project_links.md` has zero "pending" rows (or the row is explicitly declared out of scope in the writeup)
- [ ] Word count re-checked after final edits
- [ ] Upload demo notebook to Kaggle as PUBLIC; attach `GEMINI_API_KEY` via Kaggle Secrets; run all cells once
- [ ] **SUBMIT the Kaggle Writeup (not draft)** — manual human action
- [ ] Backup ZIP stored outside the repo
