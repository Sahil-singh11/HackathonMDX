# Code-Freeze Checklist — freeze at 2026-07-30 10:36 MUT (assumed)

At freeze, only bug fixes, docs, and rehearsal are allowed.

- [ ] pytest backend suite green (no skipped safety tests)
- [ ] `npm run build` green; PWA installable
- [ ] Hero demo cases rehearsed end-to-end (normal fish, octopus/date, blurry, Morisyen, offline queue, mock declaration)
- [ ] Hosted Gemma gates: run and recorded, or documented as blocked (never faked)
- [ ] Evaluation results generated and labelled with provider mode
- [ ] Writeup < 1,500 words, count file current
- [ ] Kaggle demo notebook runs top-to-bottom
- [ ] Presentation + speaker notes + failure recovery final
- [ ] Dockerfile builds; `/health` 200
- [ ] Secret scan re-run clean
- [ ] Backup ZIP created outside the repo
- [ ] `docs/REMAINING_MANUAL_ACTIONS.md` current
