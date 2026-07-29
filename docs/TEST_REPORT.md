# Test Report — 2026-07-29 (MUT)

## Backend: `pytest backend/tests -q` → **44 passed, 0 failed** (~2.4 s)

| Suite | Tests | Covers |
|---|---|---|
| test_rules_engine.py | 10 | Boundary dates (14/15 Aug, 15/16 Oct), 29-Jul-not-closed, simulated September closure, historical Jan rule never evaluated, missing source→unknown, missing measurement→unknown, unlisted species→unknown |
| test_tools_registry.py | 9 | Allow-list is exact, unknown function fails safely, invalid args fail safely, no eval/exec/globals dispatch, offline candidates/marine, deterministic rule tool, static translations, traces contain argument names not values |
| test_api_flow.py | 15 | Contract shape, rule check impossible pre-confirmation, invalid image short-circuits without model call, blurry warning, confirm flow (real + simulated date labelling), unknown-species 422, marine disclaimer, MOCK ministry labels + receipt, offline queue roundtrip, non-object payload 422, local-mode-requires-real-load, prompt-injection non-bypass, honest audio gate, today report + demo reset |
| test_privacy_and_hygiene.py | 6 | No media persisted after analysis, `.env`/`data/raw` gitignored, no key patterns in tracked files, coordinates rounded to 2 dp, permanent limitation on every analysis |
| test_dataset_leakage.py | 3 | No observation/sha crosses eval splits; non-redistributable media untracked |
| conftest fixtures | 1 | Isolated test DB, forced mock provider, demo-state reset |

## Frontend: `npm run build` → **green** (tsc strict + vite; 258 kB JS / 80.6 kB gzip)

## Evaluation harness: `evaluation/run_all.py --provider mock` → all groups green (see `docs/BASELINE_REPORT.md`)

## Release gate: `scripts/release_gate.sh` → **13/13 PASS** (secret scans incl. history, media licences, size scan, tests, build, notebooks, word count, dist key scan)

## Not run (honest)
- Hosted Gemma gates — BLOCKED, no API key (`docs/GEMMA_GATES.md`).
- Playwright browser E2E — config not yet added; covered manually via the served-app smoke test (health 200, index 200, full analyse→confirm cycle via API). Listed in `docs/REMAINING_MANUAL_ACTIONS.md`.
- Docker build — Docker daemon not exercised in-sprint; Dockerfile follows the validated local build steps.
- Adapter/audio tests — blocked with their workstreams.
