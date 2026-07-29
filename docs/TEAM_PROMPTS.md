# Team Prompts — parallel work starters

Copy-paste starters for each member's Claude/AI session (or as personal checklists). Contract freeze applies (docs/TEAM_PARALLEL_PLAN.md).

## Yuvine — backend-gemma
"Insert the GEMINI_API_KEY into .env, run `backend/scripts/run_gemma_gates.py`, fix any hosted-provider issues it reveals (google-genai function-calling round trip, structured-output ladder), then run `evaluation/run_all.py --provider hosted` and update docs/BASELINE_REPORT.md + the writeup honesty paragraph with real numbers. Do not change response schemas."

## Sahil — frontend-ux
"Polish the PWA within the frozen API: camera capture UX, crop/rotate before upload, progress states, empty states, contrast pass, reduced-motion audit, Lighthouse PWA check. Add Playwright E2E for the six hero cases in data/demo/fixtures.json. Do not rename i18n keys; add new ones in pairs (en+mfe)."

## Shirish — backend-gemma (services)
"Harden services: marine cache expiry edge cases, sync/process idempotency, declaration PDF wording review, request-size limits. Add any missing OpenAPI examples. Keep all 44 tests green and add tests for what you touch."

## Dhanesh — data-training
"Authenticate Kaggle CLI, run scripts/kaggle_push_training.sh, monitor the QLoRA run, download outputs, execute evaluate_adapter.ipynb on the held-out split, and fill training/results/ + docs/MODEL_TRAINING_REPORT.md with REAL numbers. Apply §18E acceptance strictly — no improvement, no integration. Also: grow the manifest to 10 species if time allows (fetch script takes count args)."

## Fifth member — qa-deployment + kaggle-presentation
"Deploy via deployment/render.yaml (create the Render account, set the key as a secret), validate docs/DEPLOYMENT.md checklist, update kaggle/project_links.md. Upload kaggle/notebooks/lamer_konekte_demo.ipynb as a public notebook with the Kaggle Secret. Rehearse docs/DEMO_5_MINUTES.md twice with a timer. Own the final submission checklist."

## Everyone
"Native Morisyen speakers: complete docs/MORISYEN_HUMAN_REVIEW.md and upgrade species-name statuses."
