# Deployment Plan — Lamer Konekte

## Ladder
1. **PRIMARY — public web demo.** Single Docker image: FastAPI serves API + built PWA. Platform preference: Render (free tier, no card, Docker native) → Hugging Face Spaces (Docker SDK) → Cloud Run (needs billing approval — human gate) → Railway. All need an account credential; if none exists at freeze, this is a documented human action, not a fake URL.
2. **SECONDARY — public Kaggle demo notebook** (works with Kaggle Secrets key; mock fallback without).
3. **FALLBACK — local run** (`uvicorn` + built frontend), mock mode offline, screenshots + screen recording in `presentation/assets/`.

## Artefacts
`Dockerfile` (multi-stage: node build → python runtime), `.dockerignore`, `deployment/render.yaml`, health check `GET /health`, startup `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, `docs/DEPLOYMENT.md`.

## Validation before claiming a URL
public reachability, no login, mobile viewport, hosted inference (or disclosed mock), no key in frontend bundle (`grep` the dist), no private data in the image.

## Env on the platform
`GEMINI_API_KEY` as platform secret; `PROVIDER_MODE=hosted`; SQLite on ephemeral disk is acceptable for the demo (demo-reset endpoint reseeds fixtures).
