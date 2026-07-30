# Local Run Commands

How to start Lamer Konekte on this machine. Every command below was executed and
verified on 2026-07-30 (branch `main`, Windows 11, PowerShell 5.1).

Repository root: `C:\Users\yuvin\Documents\GitHub\HackathonMDX`

---

## OPTION A — START EVERYTHING (recommended)

`run.ps1` is the project's official entry point. It creates the virtualenv if missing,
syncs backend dependencies when `requirements.txt` has changed, installs `node_modules`,
starts both servers, waits until each answers, and opens the browser.

```powershell
cd "C:\Users\yuvin\Documents\GitHub\HackathonMDX"
.\run.ps1
```

Add `-NoBrowser` if you don't want a tab opened for you.

| URL | What |
|---|---|
| http://127.0.0.1:5173 | **the app — use this one** |
| **http://127.0.0.1:5173/proof** | **Technical Proof → Manual AI test console** |
| http://127.0.0.1:8000 | backend API |
| http://127.0.0.1:8000/docs | interactive API docs |

### Manual AI test console

`/proof` carries a **Manual AI test console**: a text box that sends one free-text prompt
through the same production inference path as a real catch analysis (hosted
`gemma-4-26b-a4b-it`, production system instruction, structured-output validation,
allow-listed tools with Pydantic argument validation). Four preset buttons fill the box —
Morisyen catch intent, marine function selection, safety challenge, prompt injection — and
you then press **Run with hosted Gemma**. Results show intent, provider, exact model,
`real_inference`, latency, the functions called in order, validated argument **names**,
tool-round-trip and schema status, and the safety flags. The trace flows into the existing
"last function trace" table on the same page.

Endpoint: `POST /api/ai/test-console`, rate-limited to 6/min. Try it without the browser:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5173/api/ai/test-console `
  -ContentType 'application/json' `
  -Body '{"prompt":"Ki kondisyon lamer pou dime dan Flic-en-Flac?","language":"mfe"}' |
  Select-Object model, real_inference, schema_valid, functions_called, latency_ms
```

Other modes:

| Command | What it does |
|---|---|
| `.\run.ps1` | Dev: backend `:8000`, Vite `:5173`, hot reload |
| `.\run.ps1 -Prod` | Builds the PWA and serves it from `:8000` only. **The only mode where the service worker runs**, so use it to test offline/PWA behaviour |
| `.\run.ps1 -Status` | Report what is running; changes nothing |
| `.\run.ps1 -Stop` | Stop both servers (and any orphan holding the ports) |

Logs are written to `.run\backend.log`, `.run\backend.err.log`, `.run\frontend.log`,
`.run\frontend.err.log`. Process ids are kept in `.run\backend.pid` and `.run\frontend.pid`.

Note that the pid in those files is the **launcher**, not the process holding the port:
`uvicorn --reload` spawns a reloader child and `npm run dev` spawns node. `.\run.ps1 -Status`
reports the socket-holding pid, so the two numbers legitimately differ. `-Stop` uses
`taskkill /T`, which takes the children too — this is why killing the pid file's number by
hand can leave Vite holding `:5173`.

### Shutdown

```powershell
cd "C:\Users\yuvin\Documents\GitHub\HackathonMDX"
.\run.ps1 -Stop
```

---

## OPTION B — START SEPARATELY (two terminals)

Use this when you want to watch the two logs live, or when you are debugging one service.

### Terminal 1 — backend

```powershell
cd "C:\Users\yuvin\Documents\GitHub\HackathonMDX\backend"
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Without activating the venv, call its interpreter directly — equivalent, and what
`run.ps1` does internally:

```powershell
cd "C:\Users\yuvin\Documents\GitHub\HackathonMDX\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Ready when `http://127.0.0.1:8000/health` returns 200. Stop with **Ctrl+C**.

### Terminal 2 — frontend

```powershell
cd "C:\Users\yuvin\Documents\GitHub\HackathonMDX\frontend"
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Ready when `http://127.0.0.1:5173/` returns 200. Stop with **Ctrl+C**.

Then open **http://127.0.0.1:5173**.

---

## The backend must be on port 8000

`frontend/vite.config.ts` proxies `/api` and `/health` to a **hardcoded**
`http://127.0.0.1:8000`, and `frontend/src/api/client.ts` only ever calls relative paths
(`fetch('/api/analyse-catch')`). There is no `VITE_API_URL` to override.

So if port 8000 is taken, `run.ps1` will helpfully move the backend to 8001 — and the
frontend will then get 404s for every API call while looking perfectly healthy. If you see
that, free port 8000 and restart:

```powershell
cd "C:\Users\yuvin\Documents\GitHub\HackathonMDX"
.\run.ps1 -Stop
.\run.ps1
```

`.\run.ps1 -Status` shows which pids hold `:8000` and `:5173`.

---

## Configuration this depends on

`.env` at the repository root (git-ignored, never committed). Verified present and correct;
no secret value is reproduced here.

| Setting | Value | Why it matters |
|---|---|---|
| `GEMINI_API_KEY` | **set** (value not printed) | without it the app still runs, in clearly disclosed deterministic mock mode |
| `GEMMA_MODEL` | `gemma-4-26b-a4b-it` | the production model; `run.ps1` does not change it |
| `PROVIDER_MODE` | `hosted` | real hosted inference is the default |
| `GEMMA_PROVIDER` | `google` | official `google-genai` SDK |
| `GEMMA_TIMEOUT_SECONDS` | `60` | |
| `UPLOAD_MAX_BYTES` | `8388608` (8 MB) | larger photos are rejected before any token is spent |
| `MEDIA_RETENTION` | `delete_after_analysis` | no photo is written to disk |
| `DEMO_MODE` | `false` | |

Confirm at any time (prints no secret):

```powershell
cd "C:\Users\yuvin\Documents\GitHub\HackathonMDX"
Invoke-RestMethod http://127.0.0.1:5173/api/config/public | Select-Object model, provider_mode_default, hosted_configured
```

Expect `gemma-4-26b-a4b-it`, `hosted`, `True`. Going through `:5173` rather than `:8000`
also proves the frontend's proxy is reaching the backend.

### The experimental E2B adapter is off

`app/providers/finetuned_router.py` is not imported by any application module, and
`route()` raises `RouterUnavailable` with the reason
`adapter REJECTED by the pre-registered acceptance gate`. No environment variable in `.env`
enables it. Training succeeded, but the adapter did not pass the production acceptance
gate, so hosted Gemma 4 26B is what you will be testing.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Frontend loads but every API call 404s | backend not on 8000 (see above) | `.\run.ps1 -Stop` then `.\run.ps1` |
| `WinError 10013` on a port | the port is inside a Windows reserved range, not in use | `run.ps1` already walks past these; for Option B pick another port and update the Vite proxy |
| Backend won't start after a `git pull` | `requirements.txt` gained a dependency | `.\run.ps1` syncs it automatically; by hand: `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt` |
| Provider badge shows `mock` | key missing or blank | check `.env`, restart the backend |
| `503 UNAVAILABLE` / `500 INTERNAL` from Gemma | Google-side capacity, not a local fault | wait 30–60 s and retry; the app falls back to the **disclosed** mock meanwhile |
| Service worker / offline behaviour won't reproduce | it only runs in production mode | `.\run.ps1 -Prod`, then use `:8000` |
| Stale behaviour that contradicts the code | an old server is still holding the port | `.\run.ps1 -Status`, then `-Stop`, then start again |

Linux / WSL / Git Bash equivalents: `./scripts/start.sh`, `./scripts/start.sh --prod`,
`./scripts/stop.sh`.
