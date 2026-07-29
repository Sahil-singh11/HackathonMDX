# Model Strategy — Lamer Konekte

## Production: hosted Gemma 4
- Model: `gemma-4-26b-a4b-it` via Gemini API (official `google-genai` SDK).
- Responsibilities: image understanding, visible-characteristic extraction, constrained species suggestion, Morisyen understanding, intent classification, structured output, allow-listed function selection, final user-facing explanation (en + mfe).
- Explicit non-responsibilities: legal decisions, size verification, official species confirmation, safety-to-sail, government submission.
- Candidate retrieval: the backend supplies a shortlist (≤6) of catalogue species; the system instruction forbids answers outside the list.
- Robust output ladder: native structured output → JSON parse retry → fenced-JSON extraction → one repair request → safe uncertain fallback (`confidence_label: low`, `recommended_next_step: confirm_species`).

## Gates (run the moment GEMINI_API_KEY exists)
`backend/scripts/run_gemma_gates.py` executes and records: text smoke, image smoke, Morisyen text, structured output, function call, tool round trip, timeout, API-failure handling, latency benchmark, minimal-vs-higher thinking comparison → `docs/GEMMA_GATES.md`. **Status: BLOCKED — no key configured at baseline.**

## Local models (separate workstream, P3)
- E2B 4-bit first; E4B only after E2B succeeds and memory allows; never 12B/26B/31B locally.
- WSL reality check: 7.4 GB VM RAM, 6 GB VRAM → peak VRAM budget 5.5 GB, batch 1, small context, one model at a time, release memory between runs.
- Blocked at baseline by missing HF auth + licence acceptance. Edge bonus claimed **only** from a real local run.

## Fallback ladder (always disclosed in `provider` block + UI badge)
hosted → (timeout/failure) → mock. Local appears only after an actual model load. Mock mode never sets `real_inference: true` and never claims Gemma.
