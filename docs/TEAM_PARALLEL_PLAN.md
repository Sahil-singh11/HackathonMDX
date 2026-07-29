# Team Parallel Plan — Team Ctrl200

Branches (created from `main` after the planning baseline commit):
`backend-gemma` · `frontend-ux` · `data-training` · `qa-deployment` · `kaggle-presentation`

## Ownership
| Member | Branch | Scope |
|---|---|---|
| Yuvine | backend-gemma | Gemma providers, schemas, function registry, integration |
| Sahil | frontend-ux | React PWA, UI/UX, demo flow |
| Shirish | backend-gemma | backend services, DB, marine API, mock ministry, offline sync |
| Dhanesh | data-training | dataset, rules, evaluation, training |
| Fifth member | qa-deployment + kaggle-presentation | tests, deployment, writeup, presentation, backups |

## Contract freeze
The API contract in `docs/ARCHITECTURE.md` + `backend/app/schemas/` is **frozen** before parallel edits. Contract changes require an entry in `docs/DECISION_LOG.md` and a message to all owners.

## Merge rules (see docs/MERGE_PLAN.md)
- Small, logical commits; PR into `main`; owner of the touched area reviews.
- `main` must always keep pytest green and `npm run build` green.
- Merge order at crunch: backend-gemma → data-training → frontend-ux → qa-deployment → kaggle-presentation.
