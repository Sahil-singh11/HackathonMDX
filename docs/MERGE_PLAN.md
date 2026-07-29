# Merge Plan

1. All work branches from `main` post-baseline.
2. Rebase (not merge) from `main` before opening a PR; resolve locally.
3. `main` gate: `pytest backend/tests -q` green AND `npm run build` green (when frontend exists).
4. Conflict owners: schemas → Yuvine; DB/services → Shirish; UI → Sahil; data/eval → Dhanesh; docs/kaggle → fifth member.
5. Final integration window opens at freeze minus 4 h; only bug fixes merge after freeze (2026-07-30 10:36 MUT).
6. Tag `hackathon-submission-v1` on `main` after the public-release gate passes.
