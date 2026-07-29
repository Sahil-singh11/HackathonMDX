# Contributing

Team workflow during the hackathon:

1. Branch from `main` (`backend-gemma`, `frontend-ux`, `data-training`, `qa-deployment`, `kaggle-presentation` — see `docs/TEAM_PARALLEL_PLAN.md`).
2. The API contract (`backend/app/schemas/`) is frozen; changes need a `docs/DECISION_LOG.md` entry.
3. Before any PR into `main`: `pytest backend/tests -q` green and `npm run build` green.
4. Small logical commits; no secrets, media without licence, model weights, or databases in git (the release gate re-checks).
5. Morisyen wording changes go through `docs/MORISYEN_HUMAN_REVIEW.md`.
