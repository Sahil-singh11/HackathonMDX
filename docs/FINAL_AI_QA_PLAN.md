# Final AI QA Plan

2026-07-30 · Branch `main` @ `f31152f` · Final acceptance pass before manual user testing.
Constraints honoured throughout: no training, no threshold changes, no adapter enablement,
no architecture/product changes except verified regressions (each with a regression test).

## Inspection snapshot (measured, values never printed for secrets)

| Item | State |
|---|---|
| Branch / commit | `main` @ `f31152f`, clean tree, origin `Sahil-singh11/HackathonMDX` |
| **Repository visibility** | **PUBLIC** (GitHub API) |
| Python / Node | 3.12.2 / v22.19.0 |
| google-genai / pydantic / fastapi | 2.14.0 / 2.13.4 / 0.140.13 |
| `.env` | git-ignored (`.gitignore:2`); `GEMINI_API_KEY` **present** (value never shown) |
| Configured model / mode | `gemma-4-26b-a4b-it` / `hosted` |
| Render blueprint | Docker free tier, health `/health`, pins `PROVIDER_MODE=hosted` + `GEMMA_MODEL=gemma-4-26b-a4b-it`, key entered only in dashboard |
| Adapter weights | `kaggle/outputs/` git-ignored; readiness reads v2 metrics → REJECTED |
| Official run commands | `scripts/start.sh [--prod]` / README quick start (uvicorn :8000 + Vite :5173) |

## Execution plan

| # | Check | Mechanism | Artifact |
|---|---|---|---|
| 1 | Production model config | in-process capability probe + live smoke | `docs/FINAL_PRODUCTION_MODEL_CHECK.md` |
| 2 | Adapter stays rejected | provider introspection + **new regression tests** (env-var, API-route, provider-mode, malformed output) | tests in `backend/tests/test_final_acceptance.py` |
| 3 | Complete test battery | pytest offline + `-m live`, 5 dataset validators, archive/challenge checksums, frontend build, release gate, secret/history/weights/media scans | `docs/FINAL_AI_TEST_REPORT.md` |
| 4 | 10 live hosted gates | new `backend/scripts/run_final_live_gates.py` (real inference, redacted evidence, no chain of thought) | `evaluation/results/final_live_ai_gates.{json,csv}` + `docs/FINAL_LIVE_AI_GATE_REPORT.md` |
| 5 | Function-calling audit | registry ↔ declarations ↔ Pydantic cross-check, static dispatch scan | `docs/FINAL_FUNCTION_CALLING_AUDIT.md` |
| 6 | Local E2E flows A–F | start backend via official command; drive the **API** with httpx (browser steps documented as manual) | `evaluation/results/final_local_e2e.json` + `docs/FINAL_LOCAL_AI_E2E_REPORT.md` |
| 7 | Deployed Render | bounded cold-start wait; health/status/contract/no-secrets; safe live requests | `docs/FINAL_RENDER_AI_CHECK.md` + `evaluation/results/final_render_ai_check.json` |
| 8 | Kaggle demo notebook | static audit of `lamer_konekte_demo.ipynb` + Kaggle API status | `docs/FINAL_KAGGLE_NOTEBOOK_CHECK.md` |
| 9 | Training-evidence integrity | every documented claim cross-checked against a stored artifact; audit **fails** on any unsupported claim | `docs/FINAL_TRAINING_EVIDENCE_AUDIT.md` + `evaluation/results/final_training_evidence_audit.json` |
| 10 | One-command check | `scripts/final_ai_check.py` (`--offline/--live/--quick`) + ps1/sh wrappers, non-zero exit on failure | `evaluation/results/final_ai_check.json` |
| 11 | User guide | prerequisites, commands, 10 manual cases, troubleshooting | `docs/AI_USER_TEST_GUIDE.md` |

Fix policy: smallest safe correction for verified regressions only, each with a regression
test; never metrics, thresholds, test sets, or the adapter decision.
