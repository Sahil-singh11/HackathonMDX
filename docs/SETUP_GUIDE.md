# Team Setup Guide — Lamer Konekte

**Every command here was verified on 2026-07-29 from a clean `git clone` of `main`.** If you follow it top to bottom you get a working backend + frontend in about 5 minutes, with no API key required.

Start here: **Part 1** (everyone). Parts 2–4 are per-role.

---

## Part 0 — What you need installed first

| Tool | Version needed | Check with | If missing |
|---|---|---|---|
| Python | **3.11 or 3.12** | `python3.12 --version` | `sudo apt install python3.12 python3.12-venv` (WSL/Ubuntu) |
| Node.js | 18+ (we use 20) | `node --version` | `sudo apt install nodejs npm` or [nodejs.org](https://nodejs.org) |
| Git | any recent | `git --version` | `sudo apt install git` |

> **Windows users:** work inside **WSL** (Ubuntu), not PowerShell. The repo lives in the Linux filesystem and all paths below assume that. Open a WSL terminal and stay in it.

If `python3.12` is not found but `python3.11` is, substitute `python3.11` everywhere below — both work.

---

## Part 1 — Get it running (everyone does this)

### Step 1.1 — Clone the repo

```bash
cd ~                       # or wherever you keep projects
git clone https://github.com/Sahil-singh11/HackathonMDX.git
cd HackathonMDX
```

You should now see these folders: `backend  data  docs  evaluation  frontend  kaggle  presentation  research  scripts  training`.

> Some folders you might expect are **intentionally absent** — `backend/.venv`, `frontend/node_modules`, `storage/`, `data/raw/`. They are gitignored and get created by the steps below. That is normal.

### Step 1.2 — Backend: create the virtual environment and install

```bash
cd ~/HackathonMDX/backend
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

This takes 1–3 minutes (installs FastAPI, SQLModel, OpenCV, Pillow, google-genai, pytest…). It creates `backend/.venv/` (~420 MB, gitignored — never commit it).

> **Note on the `.venv/bin/` prefix:** we call the venv's binaries directly instead of `source .venv/bin/activate`. Both work. If you prefer activating, run `source .venv/bin/activate` once and then drop the `.venv/bin/` prefix from every command.

### Step 1.3 — Verify the backend works

```bash
cd ~/HackathonMDX/backend
.venv/bin/python -m pytest tests -q
```

**Expected output: `44 passed`.** If you get this, your backend is correct. (Any other result — go to the Troubleshooting section, do not continue.)

### Step 1.4 — Frontend: install and build

```bash
cd ~/HackathonMDX/frontend
npm install
npm run build
```

`npm install` creates `frontend/node_modules/` (~108 MB, gitignored). `npm run build` type-checks with TypeScript and produces `frontend/dist/`.

**Expected output ends with:** `✓ built in ~2s` and three `dist/...` lines. If TypeScript errors appear, the build failed — see Troubleshooting.

### Step 1.5 — Run the whole app

```bash
cd ~/HackathonMDX/backend
.venv/bin/uvicorn app.main:app --port 8000
```

Then open **http://localhost:8000** in your browser.

The backend serves the built PWA from `frontend/dist`, so **one server gives you the whole app**. You should see the Lamer Konekte landing page (language choice → Morisyen / English).

Leave this terminal running. `Ctrl+C` stops it.

**Verify it end-to-end:**
- Pick a language → Start → you land on the dashboard.
- Tap **Record a catch** → choose a photo from `data/demo/` (e.g. `octopus_cyanea_151112387.jpg`) → add note `Mo'nn gagn enn ourite` → Analyse.
- You get a species suggestion with a **grey "Demo mock" badge** — that is correct and expected (see Step 1.6).
- Confirm the species → enter measured length `45` → Check rule.
- Go to **Demo controls** → set date `2026-09-01` → redo the catch → the rule now returns **closed season** with the 2016 source and a purple SIMULATED DATE badge.

### Step 1.6 — About that "Demo mock" badge

Without a `GEMINI_API_KEY` the app runs a **deterministic offline mock** and says so on every response. This is deliberate and is *not* a bug — we never present mock output as real Gemma inference.

**The app is fully usable in this state.** You only need the key for real Gemma inference (Part 2).

---

## Part 2 — Enable real Gemma (whoever holds the API key)

### Step 2.1 — Create the `.env` file

The file does **not** exist in the repo (it is gitignored — a key must never be committed). You create it yourself:

**Location: `~/HackathonMDX/.env`** — the repo root, *not* inside `backend/`.

```bash
cd ~/HackathonMDX
cp .env.example .env
```

Then open `.env` in an editor (`nano .env` or VS Code) and set **only these two lines**:

```ini
GEMINI_API_KEY=your_actual_key_here
PROVIDER_MODE=hosted
```

Leave everything else as-is (in particular, leave `DATABASE_URL` commented out — the app picks the right path automatically). Get a key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

> **Never** paste the key into any file inside `frontend/`, never commit it, never post it in chat. Only the server reads it. `.gitignore` already blocks `.env` — verify with `git check-ignore .env` (should print `.env`).

### Step 2.2 — Run the Gemma gate tests

```bash
cd ~/HackathonMDX/backend
.venv/bin/python scripts/run_gemma_gates.py
```

This runs 10 real checks against `gemma-4-26b-a4b-it`: text, image, Morisyen, structured output, function call, tool round trip, timeout, API failure, latency, thinking comparison. Results are written to `docs/GEMMA_GATES.md` and `evaluation/results/gemma_gates.json`.

Without a key it prints `[BLOCKED]` and exits 1 — that is the honest, expected behaviour.

### Step 2.3 — Restart and confirm

Restart the server (`Ctrl+C`, then the uvicorn command again). Do a catch analysis — the badge should now read **hosted Gemma** with a model name and latency instead of the grey mock badge. Check the **Technical proof** page to see the provider status and function trace.

---

## Part 3 — Development mode (frontend work — Sahil)

For UI work you want hot reload instead of rebuilding each time. Use **two terminals**:

**Terminal 1 — backend API:**
```bash
cd ~/HackathonMDX/backend
.venv/bin/uvicorn app.main:app --port 8000 --reload
```

**Terminal 2 — Vite dev server:**
```bash
cd ~/HackathonMDX/frontend
npm run dev
```

Open the URL Vite prints (**http://localhost:5173**). Vite proxies `/api` and `/health` to port 8000 automatically (configured in `frontend/vite.config.ts`), so both work together.

Edits to `.tsx`/`.css` files hot-reload instantly. Note the **service worker only runs in production builds**, so test offline/PWA behaviour with `npm run build` + port 8000, not the dev server.

### Where frontend files live

| What | Path |
|---|---|
| Pages (one file per screen) | `frontend/src/pages/*.tsx` |
| App shell, routing, nav bar | `frontend/src/App.tsx` |
| API client (all fetch calls) | `frontend/src/api/client.ts` |
| Global state (language, profile, online) | `frontend/src/store/app.ts` |
| Offline IndexedDB queue | `frontend/src/utils/idb.ts` |
| **Translations** | `frontend/src/i18n/en.json` and `mfe.json` |
| Styles / design tokens | `frontend/src/styles.css` |
| PWA manifest, icons, service worker | `frontend/public/` |

**Adding UI text:** never hardcode a string in a component. Add the key to **both** `en.json` and `mfe.json`, then use `const t = useT()` and `t('your.key')`. Morisyen wording changes must be logged in `docs/MORISYEN_HUMAN_REVIEW.md`.

---

## Part 4 — Backend work (Yuvine / Shirish)

Run with `--reload` so the server restarts on save:

```bash
cd ~/HackathonMDX/backend
.venv/bin/uvicorn app.main:app --port 8000 --reload
```

Interactive API docs (try every endpoint in the browser): **http://localhost:8000/docs**

### Where backend files live

| What | Path |
|---|---|
| All HTTP endpoints | `backend/app/api/routes.py` |
| **Frozen API contract** (request/response shapes) | `backend/app/schemas/analysis.py` |
| Database tables | `backend/app/models/entities.py` |
| Gemma providers (hosted / mock / local) | `backend/app/providers/` |
| Provider fallback logic | `backend/app/providers/dispatcher.py` |
| **12 allow-listed functions** for Gemma | `backend/app/tools/registry.py` |
| Deterministic fisheries rules | `backend/app/services/fisheries_rules/engine.py` |
| Image quality gate | `backend/app/services/vision/quality.py` |
| Marine API client | `backend/app/services/marine/client.py` |
| Species retrieval | `backend/app/services/species/retrieval.py` |
| Gemma system instruction | `backend/app/prompts/system.py` |
| Settings / env loading | `backend/app/core/config.py` |
| Mandatory disclosure strings | `backend/app/core/limitations.py` |
| Tests | `backend/tests/` |

### Data files (edit these, not hardcoded values)

| What | Path |
|---|---|
| Species catalogue (5 species) | `data/processed/species_catalogue.json` |
| Fisheries rules + sources | `data/rules/species_rules.json` |
| Demo/hero images | `data/demo/` |
| Image licence manifest | `data/manifests/species_images.csv` |

### Rules you must not break

These are enforced by tests and are core to our safety story:

1. **Rule checks only run after human confirmation** — never inside `/api/analyse-catch`.
2. **Only `measured_length_cm` reaches the rule engine** — never the AI's `estimated_size_unverified_cm`.
3. **Missing or unverified rule ⇒ `unknown`** — never invent a value.
4. **Mock mode must never report `real_inference: true`.**
5. **Never log or return an API key, and never expose precise coordinates** (rounded to 2 dp).

Run `.venv/bin/python -m pytest tests -q` before every commit. 44 tests must stay green.

---

## Part 5 — Optional extras

### Dataset work (Dhanesh)

The 60 licensed source photos in `data/raw/` are gitignored (some are CC-BY-NC, not redistributable). Re-fetch them:

```bash
cd ~/HackathonMDX
backend/.venv/bin/python data/scripts/fetch_inaturalist_images.py 12 2
```

This queries iNaturalist live, so results may differ slightly from the original pull. If you need the *exact* original 60 files for training reproducibility, ask me — they should be copied directly rather than re-fetched.

Synthetic quality-test images (already committed) regenerate with:
```bash
backend/.venv/bin/python data/scripts/generate_synthetic_images.py
```

### Evaluation benchmark

```bash
cd ~/HackathonMDX
backend/.venv/bin/python evaluation/run_all.py --provider mock     # or --provider hosted with a key
```
Results land in `evaluation/results/`.

### Kaggle training (needs Kaggle credentials)

```bash
pip install kaggle
# then place your token at ~/.kaggle/kaggle.json (kaggle.com → Account → Create New Token)
chmod 600 ~/.kaggle/kaggle.json
cd ~/HackathonMDX && bash scripts/kaggle_push_training.sh
```

### Release gate (before making the repo public)

```bash
cd ~/HackathonMDX && bash scripts/release_gate.sh
```
13 checks: secret scans (working tree + full git history), media licences, large files, tests, build, notebooks, word count. Must print **ALL CHECKS PASSED** before the repo goes public.

---

## Troubleshooting

**`python3.12: command not found`**
Use `python3.11` instead, or install: `sudo apt install python3.12 python3.12-venv`.

**`ensurepip is not available` when creating the venv**
Install the venv package: `sudo apt install python3.12-venv`.

**`ModuleNotFoundError: No module named 'app...'` when running pytest**
You are in the wrong directory. All pytest and uvicorn commands must run from **`~/HackathonMDX/backend`**, not the repo root.

**`sqlite3.OperationalError: unable to open database file` on startup**
Fixed in the app as of commit `5c12619` — **`git pull`** and try again. It was caused by a relative `DATABASE_URL` in an early `.env`; relative paths are now resolved against the repo root regardless of where you launch the server. If you still see it, comment out the `DATABASE_URL` line in your `.env` entirely.

**Other database errors**
Delete the local DBs and re-run; they regenerate automatically:
```bash
rm -f ~/HackathonMDX/storage/*.sqlite3
```

**`npm run build` fails with TypeScript errors**
The build type-checks strictly (this is intentional). Fix the reported file/line. Do not commit a failing build — `main` must always build.

**Port 8000 already in use**
Either use another port (`--port 8001`) or kill the old server: `pkill -f uvicorn`.

**The app shows "Demo mock" even though I added the key**
Check three things: (1) `.env` is at the repo **root**, not in `backend/`; (2) it contains `PROVIDER_MODE=hosted`; (3) you restarted uvicorn — settings load once at startup.

**Browser shows a blank page / old version**
Hard-refresh (`Ctrl+Shift+R`). The service worker caches aggressively in production builds. Also re-run `npm run build` if you changed frontend code.

---

## Daily workflow summary

```bash
# start work
cd ~/HackathonMDX && git pull

# backend (terminal 1)
cd backend && .venv/bin/uvicorn app.main:app --port 8000 --reload

# frontend dev (terminal 2, only for UI work)
cd frontend && npm run dev

# before every commit
cd ~/HackathonMDX/backend && .venv/bin/python -m pytest tests -q   # 44 passed
cd ~/HackathonMDX/frontend && npm run build                        # must succeed

# commit on your branch (see docs/TEAM_PARALLEL_PLAN.md for branch ownership)
git add -A && git commit -m "..." && git push
```

Branches: `backend-gemma` (Yuvine, Shirish) · `frontend-ux` (Sahil) · `data-training` (Dhanesh) · `qa-deployment` + `kaggle-presentation` (fifth member). Rebase on `main` before opening a PR.
