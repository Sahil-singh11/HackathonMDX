# Deployment — Lamer Konekte

## Local (fallback demo of record)
```bash
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd ../frontend && npm install && npm run build
cd ../backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000 — PWA served by the backend; mock mode works fully offline
```
Insert `GEMINI_API_KEY` in `.env` (copy `.env.example`) and set `PROVIDER_MODE=hosted` for real inference.

## Docker
```bash
docker build -t lamer-konekte .
docker run -p 8000:8000 -e GEMINI_API_KEY=... lamer-konekte   # omit the key for disclosed mock mode
```

## Public URL (needs a platform account — human action)
1. **Render** (preferred, no card): connect the public repo, blueprint `deployment/render.yaml`, set `GEMINI_API_KEY` secret, deploy, verify `/health`.
2. **Hugging Face Spaces** (Docker SDK): push the repo, add `GEMINI_API_KEY` as a Space secret, app port 8000 → set `app_port: 8000` in the Space README front-matter.
3. **Cloud Run**: requires billing approval first (per autonomy rules).

## Post-deploy validation (all required before claiming a URL)
- [ ] URL loads without login on a mobile viewport
- [ ] `/health` returns 200; `/api/provider/status` shows hosted configured
- [ ] One real analysis (or clearly disclosed mock if the key is absent)
- [ ] `grep -r "AIza" ` on the served JS returns nothing
- [ ] No private data in the image (`.dockerignore` covers raw media, env, DBs)
