# Kaggle Submission Plan — Lamer Konekte

## Deliverables
1. **Writeup** `kaggle/writeup.md` — ≤1,500 words (counter file `kaggle/writeup_word_count.txt`, CI-checked by `scripts/check_writeup_count.py`). Title "Lamer Konekte"; subtitle per brief; Multimodal Track.
2. **Public repo** — flipped public only after `docs/PUBLIC_RELEASE_GATE.md` passes; tag `hackathon-submission-v1`.
3. **Demo** — primary: public web URL; secondary: public Kaggle notebook `kaggle/notebooks/lamer_konekte_demo.ipynb` (reads key from Kaggle Secrets, never prints it, full flow + mock fallback, runs top-to-bottom); fallback: local app + screenshots + recording.
4. **5-minute jury demo** — `docs/DEMO_5_MINUTES.md` + failure recovery.
5. **Final writeup submitted** (manual human action — cannot be automated).

## Word budget (target ≈1,450)
Mauritian challenge 140 · Solution 150 · Why Gemma 220 · Architecture 220 · Function calling 140 · Dataset/training/eval 190 · Morisyen/offline 120 · Safety/limitations 130 · Sprint challenges 90 · Impact/deployment 100.

## Claims policy
Only verified facts; exact model id; training reported with its **actual** outcome (including "blocked: no Kaggle auth" if that is the truth at freeze); mock clearly disclosed; no invented statistics.

## Checklist
`kaggle/submission_checklist.md` mirrors the final-validation list; every unchecked box at verification time goes into `docs/REMAINING_MANUAL_ACTIONS.md`.
