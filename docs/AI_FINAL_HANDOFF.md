# AI Workstream — Final Handoff

Branch: **merged to `main`** (true merge commit `8e2fd43`, full ai-modeling history preserved) · Updated 2026-07-30 MUT
Owner: AI modelling workstream, Team Ctrl200 · Project: Lamer Konekte

This is the single document to read when picking up the AI workstream. Everything below is
backed by committed artifacts; nothing is claimed that was not run.

---

## 1. What is in production right now

**Hosted `gemma-4-26b-a4b-it` via the official `google-genai` SDK (2.14.0), prompt-instructed
JSON, two-turn tool lifecycle.** That is the entire production AI surface.

| Component | State |
|---|---|
| Provider | `backend/app/providers/hosted.py` — lean turn-1 tool selection, structured turn-2, `coerce_to_schema()` boundary, one repair, safe uncertain fallback, disclosed mock fallback |
| Prompt | full `SYSTEM_INSTRUCTION` (the compact prompt measurably costs intent accuracy on the hosted model) |
| Latency | median ≈ 10 s end-to-end (Step 2: 33 s → 10.1 s via routing/config, no model change) |
| Fine-tuned router | `backend/app/providers/finetuned_router.py` — **DISABLED**; `readiness()` explains why; `route()` raises rather than degrading |
| Safety rails | tool allow-list + Pydantic argument validation + species confirmation + deterministic rules engine + measured-length requirement + marine disclaimer + mock-ministry labelling + hosted fallback — all server-side, all tested |

## 2. The four-step arc, in numbers

| | Step 1 | Step 2 | Step 3 (v1) | Step 4 (v2) |
|---|---|---|---|---|
| What | prove hosted Gemma works | native structured output + latency | first E2B adapter | targeted E2B adapter |
| Headline | 10/10 live gates pass | hypothesis **rejected by its own experiment**; keep prompt-JSON; 33 s → 10.1 s | intent 73.5%, **gate REJECTED** | intent **85.3%**, declaration recall **1.000**, **gate REJECTED** (tool 58.8%) |
| Tests | 93 | 146 | 192 | **314 (306 offline + 8 live)** |

Full detail: `docs/GEMMA_LIVE_GATE_REPORT.md`, `docs/AI_PRODUCTION_CONFIG_DECISION.md`,
`docs/AI_STEP3_TRAINING_REPORT.md`, `docs/AI_STEP4_FINAL_REPORT.md`.

## 3. Why the v2 adapter is rejected despite beating production

v2 tuned E2B beats hosted 26B on the identical split and prompt — 85.3% vs 70.6% intent,
100% vs 97.1% structured validity, 4.8 s vs 18.5 s median — and still fails both
pre-registered gates:

- **Tool accuracy 58.8% vs the 70% hybrid bar.** Unchanged from v1. A router that picks the
  right intent but the wrong function executes the wrong thing; the bar exists for that
  reason and was not moved.
- Gate A additionally missed on external intent (78.1% vs 80%, ≈0.6 records) and on a
  single-record `weather_query` recall dip (66.7% vs 75%).

The gates were committed **before** training (`docs/V2_PRE_REGISTERED_ACCEPTANCE_GATE.md`)
and were applied verbatim. The decision is honest, reproducible, and reversible by a better
adapter — not by a softer gate.

## 4. The one thing that clearly worked

Targeted data. v1's dominant failure (`make_declaration` recall 0.455, leaking into
`log_catch`) was attacked with 54 declaration-focused records and explicit
contrast families. Result: **1.000 precision / 1.000 recall** — every declaration correct,
zero over-predictions. This is the playbook for the remaining gaps.

## 5. Standing risks, in priority order

1. **308 of 338 training records are AI-generated, unreviewed Morisyen.** The 30 reviewed
   records were approved as written by the project owner, who is **not a verified native
   speaker** (`docs/MORISYEN_REVIEW_STEP4_REPORT.md`). Do not describe this dataset as
   native-speaker verified anywhere.
2. **Tool accuracy is flat at 58.8%** across v1 and v2 — the tool/argument head needs a
   different training signal, not just more of the same records.
3. **The 34-record internal test decides per-intent floors by single records** (2.9 pp
   each). Grow it to ≥100 before any gate with per-intent floors is applied again.
4. Hosted latency (~10 s median) remains a product constraint managed by UX, caching and
   routing — not by fine-tuning.
5. Kaggle specifics that will bite again: request `machine_shape: NvidiaTeslaT4`
   (P100/sm_60 has **no kernels** in torch 2.10+cu128); datasets mount under
   `/kaggle/input/datasets/<owner>/<slug>`; the `kaggle.json` username field may differ
   from the real key owner (`yuvineappadu`).

## 6. Immutable objects — do not touch

| Object | Protection |
|---|---|
| 32-case external benchmark (`evaluation/cases/morisyen_cases.json`) | never trained on/paraphrased; SHA-256 in `training/data/external_test_manifest.json`; enforced by validators and pytest |
| 34-record internal test (`training/data/internal_test_v1_34.jsonl`) | v1 membership pinned; verified 34/34 intact in v2 |
| 24-record challenge set (`training/data/v2_challenge_test.jsonl`) | frozen before training; SHA `23327eae…`; families nowhere in training |
| v1 snapshot (`training/archive/v1/`) | MANIFEST + CHECKSUMS; Step-3 REJECTED decision preserved verbatim |
| Compact prompt v1 | SHA `44299533f59cc907…`; changing it means minting v2 |
| Pre-registered gates | thresholds fixed before training; never adjusted after results |

## 7. How to run everything

```bash
# validators (all must pass before any training)
python scripts/validate_v2_dataset.py

# tests
cd backend && .venv/Scripts/python.exe -m pytest -q --ignore=tests/test_hosted_integration.py
cd backend && .venv/Scripts/python.exe -m pytest tests/test_hosted_integration.py -q   # needs GEMINI_API_KEY

# training pipeline (Kaggle, T4)
python kaggle/build_e2b_notebook_v2.py          # regenerate the notebook from source
pwsh scripts/kaggle_push_ai_dataset.ps1         # validators gate the upload
# push /tmp-staged notebook with machine_shape NvidiaTeslaT4, monitor, download:
pwsh scripts/kaggle_monitor_ai_training.ps1
pwsh scripts/kaggle_download_ai_outputs.ps1
```

Adapter weights live under `kaggle/outputs/` (gitignored); their checksums are recorded in
`training/archive/v1/MANIFEST.json` and `training/results/`.

## 8. Merge status — DONE

`ai-modeling` was merged into `main` as true merge commit **`8e2fd43`** (two parents, full
history — verified by ancestry check). Post-merge validation on `main`:

- `scripts/validate_v2_dataset.py` — ALL PASS
- **306 offline + 8 live hosted tests = 314 passed, 0 failed**
- frontend production build ✔ · release gate **ALL CHECKS PASSED**
- `.env` ignored ✔ · no weights tracked ✔ · E2B provider disabled ✔

Three merge-integration issues were found and fixed on `main` (none touched results):
1. Windows CRLF normalisation broke the v1-archive byte checksums — content verified
   identical after LF-normalisation; `.gitattributes` now marks checksummed evidence
   `-text`, and the verifying test accepts raw-or-LF hashes (a real edit still fails).
2. A teammate's migration tests leaked SQLite engine connections, which Windows file
   locking turns into `PermissionError` on temp-dir cleanup — engines now disposed.
3. `scripts/release_gate.sh` hardcoded the POSIX venv path — now resolves
   `bin/python` or `Scripts/python.exe`.

## 9. If a v3 adapter attempt is made

Pre-commit a v3 gate first (the v2 one is a good template — it was derived from measured
production performance). Then, in order of expected value: fix the tool-selection signal
(two-stage target or per-tool oversampling), grow the internal test, complete the Morisyen
review, and only then retrain. `make_declaration` shows the ceiling is reachable when the
data is aimed correctly.
