# Team AI model setup — hosted Gemma on every laptop

How to use the production model from any team member's machine. Every command here was
run and verified on 2026-07-30 against branch `main`.

---

## The model, in five lines

| | |
|---|---|
| **Model** | `gemma-4-26b-a4b-it` |
| **Where it runs** | Google's servers, via the official `google-genai` SDK |
| **Weights downloaded?** | **No.** Nothing is fetched, stored or loaded locally. |
| **GPU needed?** | **No.** Not even for the largest request. |
| **Internet needed?** | **Yes** — every model call is a network call. |

The fine-tuned **E2B adapter is not used.** Training succeeded, but the adapter did not pass
the production acceptance gate, so it ships disabled: it is not a selectable provider, no
environment variable switches it on, and `route()` raises `RouterUnavailable`. Do not treat
it as production.

Without an API key the app still runs, in **clearly disclosed** deterministic mock mode.
Nothing mocked is ever presented as Gemma inference.

---

## Two modes — pick one

|  | Mode A — shared Render backend | Mode B — local full stack |
|---|---|---|
| **Recommended** | **yes** | when you're working on the backend |
| You run | frontend only | backend + frontend |
| API key on your laptop | **not needed** | required, backend-only |
| Key lives in | Render environment variables | your repo-root `.env` |
| Setup time | ~2 min | ~5 min |

The **only** difference in configuration is one variable: `VITE_API_BASE_URL`.

---

## MODE A — shared Render backend (recommended)

You run the frontend; the deployed backend makes the Gemma calls with the team's key.

```powershell
# 1. Clone
git clone https://github.com/Sahil-singh11/HackathonMDX.git
cd HackathonMDX

# 2. Install frontend dependencies
cd frontend
npm install
cd ..

# 3. Configure the backend URL (interactive: choose 1)
.\scripts\configure_team_ai.ps1 -Mode shared

# 4. Start the frontend
cd frontend
npm run dev
```

Step 3 writes `frontend/.env.local` containing exactly one line:

```
VITE_API_BASE_URL=https://lamer-konekte.onrender.com
```

You can also write that file by hand — copy `frontend/.env.example`. Nothing else changes.

**5. Open http://127.0.0.1:5173/proof** (Technical Proof).

**6. Confirm all three:**

| Row | Expected |
|---|---|
| Hosted Gemma | `configured` · `gemma-4-26b-a4b-it` · google-genai SDK |
| Local Gemma (edge) | **not loaded** ← correct; no weights are used |
| Deterministic mock | `available` (fallback only) |

Then use the **Manual AI test console** on the same page: press the *Marine function
selection* preset, then **Run with hosted Gemma**. Expect `real_inference: true` and
`get_marine_conditions` in the trace.

### Two things to know about Mode A

1. **Render's free tier sleeps when idle.** The first request after a quiet period takes
   30–60 s and can look like a hang. It is not. Wake it first if you like:
   `Invoke-RestMethod https://lamer-konekte.onrender.com/health`
2. **You get whatever is deployed**, which can lag `main`. At the time of writing the
   deployed backend was serving 25 routes and did **not** yet include the blue-economy
   pillar routes or `/api/ai/test-console`. If the console is missing on the Technical
   Proof page in Mode A, that is why — ask the owner to redeploy Render from `main`, or use
   Mode B. Hosted Gemma itself was verified working on the deployed backend.

---

## MODE B — local full stack

You run FastAPI too, so you need your own authorised key.

```powershell
# 1. Clone
git clone https://github.com/Sahil-singh11/HackathonMDX.git
cd HackathonMDX

# 2 + 3. run.ps1 installs the venv, backend deps and node_modules on first run,
#         so there is nothing separate to install.

# 3. Copy the environment template
Copy-Item .env.example .env

# 4. Add your authorised key — edit .env and set:
#      GEMINI_API_KEY=<your authorised key>
#    Get one from https://aistudio.google.com/apikey, or ask the owner to share
#    the team key SECURELY (never over ordinary chat).

# 5 + 6. Leave these as the template already has them:
#      PROVIDER_MODE=hosted
#      GEMMA_MODEL=gemma-4-26b-a4b-it

# 7 + 8. Start backend and frontend together
.\run.ps1
```

`.\run.ps1` starts the backend on `:8000` and Vite on `:5173`. To run them in separate
terminals instead:

```powershell
# Terminal 1 — backend
cd "<repo>\backend"
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — frontend
cd "<repo>\frontend"
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Make sure `VITE_API_BASE_URL` is **empty or absent** in `frontend/.env.local` — that keeps
requests relative so Vite's dev proxy forwards `/api` and `/health` to your local backend.
`.\scripts\configure_team_ai.ps1 -Mode local` sets this for you and **never overwrites an
existing `.env`**.

**9. Confirm the same three Technical Proof rows** at http://127.0.0.1:5173/proof.

Linux / WSL / Git Bash: `./scripts/start.sh`, `./scripts/stop.sh`.

---

## Verify your setup

```powershell
.\scripts\check_team_ai.ps1              # infers the mode from your config
.\scripts\check_team_ai.ps1 -Mode shared
.\scripts\check_team_ai.ps1 -Mode local
```

Prints a `CHECK | RESULT | ACTION` table and exits non-zero if anything required fails. It
reports your key as *present (N chars)* — **never its value**. It checks that the backend is
reachable, reports hosted Gemma with the pinned model, has real inference on, has no local
weights loaded, does not expose the E2B adapter, and returns no key material.

Verified output on 2026-07-30: **Mode B 14/14 PASS**; **Mode A** — all shared-backend checks
PASS (model, hosted configured, `default_mode: hosted`, `real_inference: true`, local weights
not loaded, E2B absent, no key exposed).

---

## Which port am I on?

`run.ps1` moves to the next free port if `:8000` or `:5173` is taken. That matters in
Mode A: the deployed backend must allow your browser's origin. Loopback origins on **any**
port are now allowed, so `:5174` works as well as `:5173` — but only once Render has
redeployed the commit that added it. Until then Mode A needs the frontend on exactly
`:5173`. If API calls fail with a CORS error in the browser console, free port 5173 and
restart:

```powershell
.\run.ps1 -Stop
.\run.ps1
```

---

## Security rules — no exceptions

**Never:**

- commit `.env` (it is git-ignored; `.env.example` is the template that *is* committed);
- put the API key in frontend code;
- put the API key in **any** `VITE_*` variable — Vite inlines those into the JavaScript
  bundle in clear text, so it would be published to every visitor. There is deliberately no
  `VITE_GEMINI_API_KEY`, and a test asserts one never appears;
- send the key through ordinary chat (Slack/WhatsApp/email);
- show the key on screen during the presentation — the Technical Proof page never displays
  it, and no API response contains it;
- use the rejected E2B adapter as production;
- download Gemma 4 26B weights. They are not needed and are ~50 GB.

**If the team shares one key:** store it **only** in Render's environment variables and use
Mode A. That way exactly one copy exists, no teammate needs it on disk, and rotating it is a
single change in one place. If a key is ever exposed, revoke it in Google AI Studio
immediately — rotation is cheap, a leaked key is not.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Technical Proof shows `no API key` | Mode B without a key, or Render has none | add it to `.env` and restart, or ask the owner about Render |
| Provider badge says `mock` | no key, or hosted call failed | the disclosure text says which; retry a hosted failure |
| First Mode A request hangs ~40 s | Render free tier waking | wait; hit `/health` once first |
| CORS error in the browser console | frontend not on an allowed origin | free `:5173` and restart (see above) |
| `503 UNAVAILABLE` / `500 INTERNAL` from Gemma | Google-side capacity | wait 30–60 s and retry; not your setup |
| Manual AI console missing in Mode A | Render is behind `main` | ask the owner to redeploy, or use Mode B |
| Backend won't start after `git pull` | `requirements.txt` changed | `.\run.ps1` syncs automatically |
| `WinError 10013` binding a port | Windows reserved port range, not a firewall | `run.ps1` already walks past these |
