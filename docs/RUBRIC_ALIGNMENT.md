# Rubric Alignment — Lamer Konekte

| Rubric area | Points | How we score them | Evidence artefacts |
|---|---|---|---|
| Gemma 4 Integration | 30 | Hosted `gemma-4-26b-a4b-it` via official `google-genai` SDK does image understanding, constrained species suggestion, Morisyen intent, structured output, and **native function calling** with a tool-response round trip. Candidate retrieval keeps prompts grounded. Provider badge + latency + function trace visible in UI ("Technical proof" page). | `backend/app/providers/hosted.py`, `backend/app/tools/`, gate results in `docs/GEMMA_GATES.md`, UI trace page |
| Innovation & Impact | 30 | Morisyen-first Blue-Economy product for artisanal fishers: catch documentation, deterministic sourced fisheries rules, marine conditions, offline-first queue, mock ministry declaration flow showing a realistic e-government path. | writeup, README, impact page |
| Functionality | 20 | Full E2E flow: photo → quality gate → suggestion → mandatory confirmation → measured length → deterministic rule → log → declaration → mock receipt; offline queue; marine forecast with cache. | pytest suite, Playwright script, demo |
| Morisyen bonus | up to 10 | Complete en/mfe i18n, ≥30 Morisyen evaluation cases, Morisyen replies from the model path, human-review register for critical wording. | `frontend/src/i18n/mfe.json`, `evaluation/cases/morisyen_cases.json`, `docs/MORISYEN_LANGUAGE_REPORT.md` |
| Presentation & Writeup | 20 | ≤1,500-word writeup with verified claims only; 5-minute rehearsed demo script with failure recovery; honest limitations. | `kaggle/writeup.md`, `presentation/`, `docs/DEMO_5_MINUTES.md` |

## Honesty rules that protect the score
- Mock mode is always labelled; never presented as Gemma inference.
- Training claimed only if a run + held-out eval actually completed.
- Edge bonus claimed only if a local Gemma model actually ran (currently blocked: no HF auth).
- Every unrun gate is listed as blocked in the final report, not omitted.
