# Master Execution Plan — Lamer Konekte (Team Ctrl200)

Plan basis: baseline of 2026-07-29 14:26 MUT (`docs/BASELINE_ENVIRONMENT.md`), assumed deadline 2026-07-30 13:36 MUT, freeze 10:36, verification 12:36. Multimodal Track; rubric: Gemma 30 / Innovation 30 / Functionality 20 / Presentation+Writeup 20 / Morisyen-or-edge bonus 10.

## Hard constraints discovered at baseline

- **No GEMINI_API_KEY configured** → hosted Gemma gates blocked until a human inserts the key. All hosted-provider code is built and testable the moment the key lands; the app runs in disclosed mock mode meanwhile.
- **No Kaggle credentials** → training jobs cannot be launched from this machine yet. Notebooks and push scripts are prepared so training starts within minutes of authentication.
- **No HF token / licence acceptance** → local edge proof is P3 and may not happen; never claimed unless a model actually runs.

## Phases, priorities, dependencies

| # | Phase | Priority | Depends on | Acceptance criteria |
|---|---|---|---|---|
| 1 | Inspect + secret protection + plans | P0 | — | Baseline doc, clean secret scan, `.gitignore`, plans committed |
| 2 | Species data + rules + research registers | P0 | 1 | `species_catalogue.json` (5 species), versioned sourced `species_rules.json`, boundary-date data |
| 3 | Backend (FastAPI, providers, tools, marine, rules engine) | P0 | 2 | All contract endpoints up; mock mode fully offline; hosted provider code-complete; pytest green |
| 4 | Backend tests incl. critical safety assertions | P0 | 3 | All critical assertions in §24 of the brief pass; failures reported honestly |
| 5 | Frontend PWA (mobile-first, en/mfe i18n, offline queue) | P0/P1 | 3 (contract) | Production build passes; hero flow works against backend |
| 6 | Evaluation harness + Morisyen cases + baseline vs mock | P1 | 3 | ≥30 Morisyen cases; runner produces results CSV/JSON labelled by provider mode |
| 7 | Kaggle notebooks + writeup + checklist | P0 | 3, 6 | Writeup < 1,500 words with count file; notebooks valid JSON, run top-to-bottom in mock mode |
| 8 | Security/privacy docs, Dockerfile, deployment plan | P0 | 3, 5 | Docker build config, health check, docs complete |
| 9 | Presentation + demo scripts + failure recovery | P0 | 5 | pptx + speaker notes + 5-minute script |
| 10 | Training automation (prepared; launch gated on Kaggle auth) | P1 | 6 | train/val/test JSONL, notebooks, push scripts ready; blocker documented if auth absent |
| 11 | Public-release gate + final validation + final report | P0 | all | Gate checklist all green; report honest about every unrun gate |

## Test gates
- Gate T1: pytest backend suite green before frontend integration.
- Gate T2: frontend `npm run build` green before deployment work.
- Gate T3: hosted Gemma smoke tests — **blocked until key**; recorded as blocked, never faked.

## Training gates
- Gate G1 (Kaggle auth) → G2 (GPU inspect) → G3 (warm-up run) → G4 (held-out eval ≥ baseline on ≥1 metric, no safety regression) → integrate. Any gate failure: keep hosted Gemma, report honestly.

## Deployment gates
- D1: Docker image builds and `/health` returns 200 in mock mode.
- D2: public URL reachable without login (needs a platform credential — human action if absent).
- Fallback demo path (always available): local run + mock mode + Kaggle notebook + screenshots.

## Cut list (in order, if behind)
1. decorative animation; 2. advanced map; 3. species beyond five; 4. full audio; 5. edge proof; 6. larger training run.

**Never cut:** real-Gemma provider path, function calling, mandatory confirmation, deterministic rules, disclosures, writeup, public repository, fallback demo.

## Manual actions (humans)
1. Put `GEMINI_API_KEY` in `.env`, then run `backend/scripts/run_gemma_gates.py`.
2. Kaggle auth, then run `scripts/kaggle_push_training.sh` (or `.ps1` from Windows).
3. Record real Morisyen audio (consented) if audio workstream is attempted.
4. Verify official deadline and adjust `docs/TIMEBOX.md`.
5. Flip repo to public after `docs/PUBLIC_RELEASE_GATE.md` passes (script provided; gh is authenticated).
6. Submit the final Kaggle Writeup (cannot be automated).
