# Work Log — Shirish

**Period:** 2026-07-29 (single working session)
**Role:** Backend hardening & deployment → shore-side traceability (Lane C prerequisite)
**Status at time of writing:** all work below is merged into `origin/main`

---

## Summary

Six pieces of work, in order: environment setup, a secret leak fix, backend hardening (merged), a full architectural audit, two critical fixes from that audit, and the traceability ledger that the frontend Lane C brief assumes exists.

| # | Work | Commit | State |
|---|---|---|---|
| 1 | Local environment brought up (venv, deps, build, `.env`) | — | Done |
| 2 | **Live API key removed from `.env.example`** | — (working tree, pre-commit) | Done |
| 3 | Backend hardening: throttle, marine pre-warm, OpenAPI, seed script | `eede8eb` → merged `0231dd5` | **In `main`** |
| 4 | Deep structural analysis of the whole project | *(file lost — see §7)* | Superseded |
| 5 | Non-blocking startup fix (audit finding W2) | `4acff21` | **In `main`** |
| 6 | Traceability ledger + public verification + officer views | `16291c9` → merged PR #5 `e0278ad` | **In `main`** |

---

## 1. Environment setup

The documented setup command did not work on Windows:

```bash
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Two reasons: there is no `python3.12` executable on this machine (the interpreter is `python`, Python 3.12 at `…/Programs/Python/Python312`), and Windows venvs put binaries in `.venv/Scripts/`, not the POSIX `.venv/bin/`.

**Working equivalent:**
```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
```

Also completed: `npm install` (76 packages), `npm run build` (TypeScript + Vite, clean), and `.env` created from the template.

**Discovered while first running the app:** `backend/storage/` does not exist on a fresh clone and nothing creates it, so SQLite failed at startup with `unable to open database file`. Creating the directory fixed it. This was later fixed properly upstream by `5c12619`, which resolves relative SQLite paths against the repo root.

---

## 2. Security fix — live API key in a committed template

`.env.example` is a public template tracked in git (`.gitignore` excludes `.env` and `.env.*` but explicitly re-includes `.env.example`). It contained a **real, active** `GEMINI_API_KEY` value rather than a blank placeholder.

It had not yet been committed, so it never reached GitHub — but the next `git add .` would have published a live credential to a public repository.

**Actions taken:** reverted `.env.example` to a blank `GEMINI_API_KEY=`, moved the real key into `.env` (gitignored), and confirmed the key had not leaked through the WhatsApp-transferred setup guide (that file contained only `your_actual_key_here`).

**Still recommended:** rotate the key in Google AI Studio. It sat in plaintext in a tracked-file path, and rotation is cheap insurance.

---

## 3. Backend hardening — `eede8eb`, merged as `0231dd5`

Four assigned tasks. All shipped with tests.

**Marine cache pre-warm.** Grand Baie, Mahébourg and Flic-en-Flac are fetched and cached at startup so the demo never waits on a live Open-Meteo round trip. Each location is isolated in its own `try/except` so one failure cannot block the others or crash boot. Verified live: all three cached from real Open-Meteo data, subsequent requests return `"cached": true` instantly.

**Per-IP throttle on `/api/analyse-catch`.** New `backend/app/core/ratelimit.py` — an in-memory sliding-window limiter, 10 requests/minute, returning `429` with a `Retry-After` header. It reads `X-Forwarded-For` first, because Render sits in front as a reverse proxy and `request.client.host` alone would be the proxy's address for every visitor. Verified live: requests 1–10 returned `200`, the 11th `429`, and `/api/demo/reset` clears it.

**OpenAPI examples and summaries** on the endpoints judges open first — analyse-catch, confirm, species, catches, marine-conditions, and both declaration endpoints. The analyse-catch example is a real captured API response, not a fabrication. `backend/app/schemas/analysis.py` was deliberately **not** touched: it is marked FROZEN and requires a decision-log entry to change, so all documentation lives in route decorators instead.

**Demo seed script** — `backend/scripts/seed_demo_catches.py`. Posts 12 realistic catches (all 5 species, 6 Mauritius lagoon locations, dates spread across 10 days) through the real `/api/catches` endpoint, so seeded rows take exactly the same validation and rule-check path as a genuine catch. Idempotent, with `--force` to override.

**Known downstream effect:** the throttle starved the in-process evaluation harness, which fires 40+ analyse calls from one address. Fixed upstream in `74149d3` by resetting the limiter between benchmark calls.

---

## 4. Deep structural analysis

A full audit of architecture, data flow, trust boundaries, completeness and weaknesses, with every claim cited to a verified file and line.

Ten weaknesses were ranked by impact. The three that mattered:

1. **The live demo was serving stale code.** Verified against `lamer-konekte.onrender.com/openapi.json`: it predated the hardening merge entirely — no rate limiting, no OpenAPI examples, no `capabilities` block. The public URL was therefore completely unthrottled, which was the exact exposure the hardening work existed to close. **Now resolved** — the live site returns the rate-limit documentation.
2. **Startup blocked on three synchronous network calls** (my own bug — see §5).
3. **Hosted latency dominates UX** — median 21.7 s per call, species agreement 0.50. `hosted.py` documents why the usual fix is unavailable: capping `max_output_tokens` returns empty text because the model emits hidden thinking tokens first.

Other findings still open at the time of writing: dead schema (`FisherProfile`, `Species`, `SpeciesRule` tables are created but never read — the app uses JSON files), the tool registry's executable surface (12 handlers) being wider than its declared surface (9), no `429` handling in the frontend, and the test suite spending real API quota by default with no marker to deselect the live tests.

---

## 5. Non-blocking startup — `4acff21`

*This fixed a flaw in my own §3 work.*

The marine pre-warm ran **synchronously inside the startup hook**. Each location makes up to 2 attempts at a 10 s timeout, so worst case was **3 × 2 × 10 s = 60 s of blocked boot** before uvicorn served anything — enough to fail Render's health check. Intended to reduce demo latency, it could instead prevent the app from starting.

**Fix:** `asyncio.create_task(asyncio.to_thread(...))` so readiness never waits on the network, plus a `marine_prewarm_on_startup` setting (default `true`) disabled in `tests/conftest.py` so the suite no longer touches the network at startup.

**Measured:** `/health` returned 200 in **111 ms**, versus ~3 s happy-path (up to 60 s worst case) before. The log confirms `Application startup complete` fires *before* any pre-warm activity.

---

## 6. Traceability ledger — `16291c9`, merged as PR #5 `e0278ad`

### Why this, and not the Lane C frontend

The Lane C brief opens with "Read CLAUDE.md first" and consumes frozen primitives (`ui/Table`, `ui/DateField`), `lib/api` stubs and `lib/offline`. At the time this was assigned, **Phase 0 had not merged** — none of those existed on `main` or any remote branch. The prompt pack's own rule is explicit and stated twice: *"Phase 0 merges to `main` before anyone else opens Claude Code."* Building Lane C pages then would have meant inventing the primitives I am forbidden to touch, guaranteeing a conflict when Phase 0 landed.

Meanwhile Lane C surfaces 2 and 3 assume *"the catch records form a hash chain"* and call `verifyLedger` / `verifyCertificate`. **No chain existed**, and the frontend ownership map covers only frontend files — so nobody was assigned to build it. Backend is my lane, it was unblocked, and it is a hard prerequisite for two of my three surfaces. So that is what I built.

### What it does

`LedgerEntry` is an append-only hash chain in its own table — no `CatchRecord` migration, so existing data is untouched. Each entry commits to the record's canonical content **and** to the previous entry's hash, so altering or deleting any historical record breaks every link after it.

**A deliberate design decision:** the chain seals the substantive catch facts (`species_id`, `measured_length_cm`, `count`, `capture_date`, `fishing_area`, coordinates) but **not** `legal_status` or `legal_note`. Otherwise the newly verified GN 167/2016 mantle-size rule — or any future rules correction — would invalidate the entire ledger on re-check. A test pins this behaviour.

`verify_chain()` walks from genesis and names the **first** break and its exact record, distinguishing four cases: `record_modified`, `record_missing`, `prev_hash_mismatch`, `entry_hash_mismatch`.

**Endpoints** (matching the `lib/api` names in the brief):

| Endpoint | Purpose |
|---|---|
| `GET /api/ledger` | Inspect the chain (officer ledger view) |
| `GET /api/ledger/verify` | Walk chain → `intact` / `broken` + first bad record |
| `GET /api/verify/{id}` | Public, no auth → `verified` / `not_found` / `chain_broken` |
| `GET /api/submissions` | Officer submissions list |
| `GET /api/submissions/{id}` | Detail with per-record ledger status |

**Honesty guardrails**, because Surface 3 explicitly says not to overclaim. Every response carries a scope note stating the chain proves a record is *unaltered since it was logged*, **not** that the reported details are true, and that it is a local chain, not a distributed blockchain. `/api/verify/{id}` returns an explicit `not_verified` list: species is AI-assisted and fisher-confirmed rather than independently verified, the measurement is self-reported, and legality is informational only.

### Bug caught during development

`/api/demo/reset` deletes catch records. Without also clearing `LedgerEntry`, the chain would point at deleted records and report **broken forever** after any reset — which would have failed live during the demo. `LedgerEntry` was added to the reset sweep, with a test.

Also required: `declarations/service.py` now includes `record_id` in each catch line, so the officer view can resolve a submission row to its ledger entry. Additive, and the PDF export is unaffected.

### Verified end-to-end on a live server

- 12 seeded catches sealed; each entry's `prev_hash` matched the prior entry's `entry_hash`.
- Before tampering: `intact`, 12 of 12 verified.
- Edited record 5 directly in the database, behind the API's back → `broken`, `verified_through: 4`, `reason: record_modified`, naming the exact record ID.
- All three public verdicts exercised: `verified`, `chain_broken`, `not_found`.
- Officer detail view showed the tampered record (`x500`) beside the broken-chain flag at seq 5.

**Tests:** 16 new, covering sealing, chain linkage, all four tamper types, idempotency, the rules-recheck exemption, the empty chain, all three public verdicts, and reset behaviour. Full suite **156 passing** (excluding the live-API tests, which cost real quota).

---

## 7. Note on a lost file

The §4 analysis was written to `docs/PROJECT_ANALYSIS.md` but never committed, and was lost when the working tree moved on. Its two critical findings (W1 stale deploy, W2 blocking startup) were both acted on and are fixed. The remaining findings are summarised in §4 above; the full document can be regenerated on request.

---

## Current state and what is next

**Phase 0 has now merged** (`c001b7e` — shell, UI primitives, themes, router, `CLAUDE.md`), and `bcc2796` has already wired the shore-side API to this ledger. **Lane C's frontend is unblocked as of now.**

Remaining Lane C work, per the brief:

- `/declaration` — period presets, live preview panel, prepare → review → receipt, blocked submission when records are unconfirmed, every state designed
- `/authority` — own top bar (not `components/shell`), no ambient animation, overview stats, sortable submissions table, submission detail with per-record verification, **Leaflet map** with offline coordinate-list fallback, **ledger view** (the stated differentiator — the backend for it is done)
- `/verify/:id` — public verdict page, printable, no auth (backend complete, three verdicts live)

Constraints to respect: `styles/tokens.css` and `components/ui/*` are frozen — wrap primitives inside `components/{declaration,authority,verify}`, never edit them. Branch `fe/authority` off current `main`. Fill in only the five Lane C functions in `lib/api`, keeping alphabetical positions.

**Also still open:** rotate the Gemini API key (§2), and the outstanding audit items from §4 — dead schema removal, tool allow-list tightening, frontend `429` handling, and a `live` pytest marker so the default suite stops spending API quota.
