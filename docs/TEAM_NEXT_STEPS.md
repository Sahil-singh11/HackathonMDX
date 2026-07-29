# Team Next Steps — from now to submission

Written 2026-07-29 ~16:30 MUT. **~18 h to feature freeze (10:36 tomorrow), ~21 h to the assumed deadline (13:36).** Everyone has pulled `main`; hosted Gemma is live and all ten gates pass.

## Where we are (verified, not aspirational)

- ✅ Real Gemma inference working through the app: photo → correct octopus suggestion, Morisyen replies, `get_marine_conditions` function-calling round trip.
- ✅ 50 backend tests green, frontend builds, release gate 13/13, writeup 1,384/1,500 words.
- ⚠️ Hosted latency is **16–25 s per model call** on our key tier. This is now our single biggest demo risk and shapes the frontend work below.
- ⏳ Not done: training run (needs Kaggle auth), public deployment, Morisyen native review, public flip + submission.

---

## Workstream 1 — Training & fine-tuning — **Dhanesh** (support: Yuvine)

Goal: a real QLoRA attempt with held-out evaluation before freeze. Budget ~6–8 h wall-clock, mostly Kaggle GPU time you can leave unattended.

1. **Auth (15 min):** `pip install kaggle`; kaggle.com → Account → Create New Token; save to `~/.kaggle/kaggle.json`; `chmod 600 ~/.kaggle/kaggle.json`.
2. **HF access (15 min):** Hugging Face account → accept the Gemma licence on the `google/gemma-4-e2b-it` model page → create a read token → add it as Kaggle Secret `HF_TOKEN`.
3. **Push data + notebook (10 min):** `bash scripts/kaggle_push_training.sh` (creates the PRIVATE dataset `lamer-konekte-training` and starts `train_gemma4_qlora.ipynb` on GPU).
4. **Hardware gate + warm-up:** the first cells print GPU/VRAM/BF16 and run a tiny warm-up. **If OOM at warm-up → switch to `train_gemma4_text_adapter.ipynb` (Mode B) immediately. Do not fight the multimodal fit.**
5. **Monitor:** `bash scripts/kaggle_monitor_training.sh` (polls every 2 min). Expected full run: 1–3 h on Kaggle T4/P100.
6. **Download + evaluate:** `bash scripts/kaggle_download_outputs.sh`, then run `kaggle/notebooks/evaluate_adapter.ipynb` against `training/data/test.jsonl` (8 held-out records + safety cases).
7. **§18E decision (strict):** integrate ONLY if structured validity, unsafe rate and false confidence are not worse AND ≥1 target metric improves. Otherwise: production stays on hosted Gemma; write the real numbers into `training/results/metrics.json`, `comparison.csv`, `training_log_summary.md` and `docs/MODEL_TRAINING_REPORT.md`. **A well-documented "attempted, not integrated" is full rubric credit for the training story — a broken integration is not.**
8. **Hard stop:** if the run hasn't produced an adapter by **07:00**, kill it, document the state, move to helping QA. Never let training eat the demo.

Also yours: grow the dataset to 10 species *only if* everything above is done (`data/scripts/fetch_inaturalist_images.py 12 2` after extending the SPECIES dict + catalogue + rules with `unavailable` entries).

---

## Workstream 2 — Frontend & UI polish — **Sahil**

Goal: the app must *feel* designed, and the ~20 s Gemma latency must feel intentional, not broken. Work on `frontend-ux`, rebase on `main` often. Every change: `npm run build` must stay green.

### 2.1 Latency UX (top priority — do this first, ~2 h)

The analyse call takes 15–30 s in hosted mode. A dead spinner for 20 s kills the demo. In `frontend/src/pages/CatchFlow.tsx`:

- Replace the single "Analysing…" state with a **staged progress narrative** that advances on a timer (roughly: 0 s "Checking photo quality…" → 2 s "Photo OK — asking Gemma…" → 8 s "Gemma is examining the visible features…" → 15 s "Preparing the suggestion…"). Add the strings to BOTH `i18n/en.json` and `i18n/mfe.json` (e.g. `catch.progress.1..4`).
- Show a **skeleton card** (grey shimmer blocks where the suggestion will appear) instead of a spinner. Pure CSS in `styles.css` — a `.skeleton` class with a `@keyframes` shimmer; respect `prefers-reduced-motion` (already handled globally).
- Show the uploaded photo prominently during the wait (it's already in `preview`) — people stare at their own photo happily for 20 s.
- Add a cancel button that aborts the fetch (`AbortController` in `api/client.ts`).

### 2.2 Species confirmation with images (~1.5 h)

The confirmation list is text-only. We ship 8 licensed hero photos in `data/demo/` — the backend serves the repo dir? No: copy the 8 hero images to `frontend/public/species/` (they are CC0/CC-BY, attribution already in the manifest — add a one-line credit in the Privacy/About page). Then in the species option buttons show a 56×56 rounded thumbnail per species. Selecting becomes visual, faster, and demos beautifully.

### 2.3 Visual polish pass (~2–3 h, in this order)

1. **Landing page hero:** add a subtle SVG wave divider between the navy header and content (inline SVG, two `<path>` layers in `--turquoise`/`--seafoam` at 20% opacity). One decorative element, used once.
2. **Dashboard tiles:** current 9 tiles are equal weight. Make **Record a catch** a full-width hero tile (bigger icon + one-line description) and demote Demo/Privacy/About into a smaller "more" row. Fishers' three moments (Marine / Catch / Log-Declare) should read as the top row.
3. **Typography rhythm:** in `styles.css` set page `h2` to 1.35 rem, add `letter-spacing: -0.01em` to headings, and increase card padding to 1.1 rem. Consistent 0.75 rem gaps everywhere (audit the ad-hoc margins).
4. **Rule result screen:** it's the emotional peak of the demo. Give `closed_season` / `allowed` / `unknown` a large iconed banner (X-octagon coral / check-circle green / help-circle amber from lucide), the rule ID + source as a small "receipt" card, and keep the verify-notice visible without scrolling on a 640×360 phone viewport.
5. **Badges:** unify — all badges same height (22 px), same radius; provider badge gets a tiny dot icon (green pulse when hosted).
6. **Empty states:** History and Queue when empty should show a friendly line + icon + CTA button to the catch flow, not just grey text.
7. **Outdoor readability check:** crank screen brightness simulation — the muted text `#5a6b84` on white must stay ≥4.5:1 (it is, but verify anything you add with a contrast checker).

### 2.4 Verification (~1 h)

- `npm run build` + serve via backend; walk all six hero cases from `data/demo/fixtures.json` on a 390 px viewport.
- Lighthouse (Chrome DevTools) → PWA installable, a11y ≥ 90. Fix what it flags.
- Optional if time: Playwright — `npm i -D @playwright/test`, one spec that runs the mock-mode catch flow (analyse → confirm → rule) headless; wire into `qa-deployment` branch.

**Cut order if time runs out:** 2.3.1 wave art → 2.3.5 badges → 2.2 images. Never cut 2.1 (latency UX).

---

## Workstream 3 — Gemma quality & prompt tuning — **Yuvine**

Goal: sharpen real-inference quality using the hosted evaluation results (`evaluation/results/baseline.json`, `morisyen_results.csv`).

1. Read every failed/slow case in `morisyen_results.csv`. Classify: wrong intent vs slow vs safety wobble.
2. **Latency levers** (in `backend/app/prompts/system.py` and `hosted.py`): add "Keep replies under 40 words." to the OUTPUT section; cap `max_output_tokens` (add `max_output_tokens=300` to `GenerateContentConfig`) — shorter generations are the main latency lever we control.
3. If intent errors: add 2–3 few-shot lines to the system instruction (cheap, effective). Re-run `evaluation/run_all.py --provider hosted` after each change — never tune blind.
4. Verify the confidence labels correlate with correctness on the 60-image set (spot-check 10 images across species via the API). If everything comes back "high", tighten the instruction: "Use 'high' only when diagnostic features are clearly visible."
5. Keep `pytest` green; you own `schemas/` — no contract changes without a decision-log entry.

---

## Workstream 4 — Backend hardening & deployment — **Shirish** + **fifth member**

**Shirish (~3 h):**
1. Pre-warm marine cache on startup for the 3 demo locations (Grand Baie, Mahébourg, Flic-en-Flac) so the demo never waits on Open-Meteo.
2. Add simple per-IP request throttling on `/api/analyse-catch` (in-memory counter, 10/min) — the public URL will be probed.
3. OpenAPI examples for the four main endpoints (FastAPI `openapi_extra` or response examples) — judges open `/docs`.
4. Review declaration PDF wording with a Morisyen speaker.

**Fifth member — deployment + submission logistics (~4 h):**
1. **Render deploy (do this early — it's the highest-risk unknown):** create account (free, no card) → New → Blueprint → connect the repo (needs it public *or* grant Render access to the private repo) → `deployment/render.yaml` is auto-detected → set `GEMINI_API_KEY` in the dashboard → deploy → run the `docs/DEPLOYMENT.md` validation checklist → put the URL in `kaggle/project_links.md`.
   - Fallback if Render fights you >90 min: Hugging Face Spaces (Docker SDK, `app_port: 8000`).
2. **Kaggle demo notebook:** upload `kaggle/notebooks/lamer_konekte_demo.ipynb` as a public notebook, attach `GEMINI_API_KEY` as a Kaggle Secret, Run All once, save the version. This is our guaranteed demo of record.
3. **Rehearsals:** two full timed runs of `docs/DEMO_5_MINUTES.md` tonight with the real latency (the script's beats absorb one ~20 s call each; if a second analyse is needed live, use the mock toggle and *say so* — honesty plays well).
4. Nightly backup ZIP + git bundle (same commands as in the final report).

---

## Workstream 5 — Morisyen native review — **any native speaker, 45 min, tonight**

Open `docs/MORISYEN_HUMAN_REVIEW.md`, review the 7 critical strings + 5 species names, correct `frontend/src/i18n/mfe.json` and `data/processed/species_catalogue.json`, fill the reviewer column, upgrade statuses in `research/SPECIES_NAME_REGISTER.md`, rebuild. This is cheap and directly protects the 10-point Morisyen bonus.

---

## Schedule & control points

| Time (MUT) | Checkpoint |
|---|---|
| tonight 20:00 | Dhanesh: training running on Kaggle · Sahil: latency UX merged · fifth: Render URL live or fallback decided |
| tonight 23:00 | Morisyen review done · first full rehearsal done |
| 07:00 | Training hard stop → §18E decision + reports · UI polish frozen |
| **10:36** | **FEATURE FREEZE** — bug fixes/docs/rehearsal only; run `scripts/release_gate.sh` |
| 12:00 | Public flip (Sahil: admin for YedTorma or manual flip) · tag · notebook public · links file has zero "pending" |
| **12:36** | Final verification → **submit the writeup (not draft)** |

Merge rules unchanged (`docs/MERGE_PLAN.md`): rebase before PR, `main` keeps 50 tests + build green. Contract (`backend/app/schemas/`) stays frozen.
