# Final Production Model Check

Verified 2026-07-30 on `main`. Machine-checked by
`backend/tests/test_final_acceptance.py` and the live gate runner.

---

## 1. Production path — exactly one model

| Property | Verified value | How |
|---|---|---|
| Provider name | `google-genai` | `/api/provider/status`, capability surface |
| **Exact model** | **`gemma-4-26b-a4b-it`** | `settings.gemma_model`, live gate 0, Render status |
| SDK | **google-genai 2.14.0** (official) | `importlib.metadata`, `from google import genai` |
| Text support | yes | live gates 1, 2, 9 |
| Image support | yes | live gates 5, 6, 7 (real photo bytes) |
| Structured-response support | yes | 100% structured validity, frozen Pydantic contract |
| Function-calling support | yes | live gates 3, 4, 10 (native `function_call` parts) |
| Timeout handling | 90 s `HttpOptions`, per-route profile timeouts (45/60/75 s) | `app/inference/gemma_hosted.py`, `app/providers/profiles.py` |
| Failure fallback | hosted → one repair → safe uncertain → **disclosed** mock | dispatcher + `FALLBACK_DISCLOSURE` |
| Latency instrumentation | per-stage `stages_ms` + `provider.latency_ms` | E2E flow F, live gate artifacts |
| `real_inference` metadata | present and honest | E2E flow F, Render check |

**Note on code location:** the implementation moved to `app/inference/gemma_hosted.py` in
the Task-1a inference-provider migration; `app/providers/hosted.py` is now a forwarding
shim. The acceptance test audits the **real module** (reading the shim would pass
vacuously) and asserts `hosted.analyse is gemma_hosted.analyse` so both import paths agree.

## 2. No silent substitution — each ruled out by a test

| Risk | Verified |
|---|---|
| Gemini | no `gemini-*` literal in the implementation; model comes from `settings.gemma_model` |
| Gemma 3 / other size | no `gemma-3*` literal; `Settings(_env_file=None)` default resolves to `gemma-4-26b-a4b-it` |
| Local E2B adapter | not a `ProviderMode` value; dispatcher contains no reference to it; `route()` raises |
| Deterministic mock | selectable only as an explicit fallback, always `simulated=True` / `real_inference=False`, always carries a disclosure |

`test_no_environment_default_substitutes_another_model` constructs `Settings` with
`_env_file=None` and an unset `GEMMA_MODEL`, proving the **default** is the pinned model —
so a missing/blank env var cannot quietly change the production model.

## 3. Mock mode — permitted, always labelled

Mock exists solely as a fallback. It reports `provider_name="deterministic-mock"`,
`model="none"`, `real_inference=False`, `simulated=True`, and a `MOCK_DISCLOSURE`; when it
replaces a failed hosted call the response additionally carries `FALLBACK_DISCLOSURE`
("…not real model inference").

The E2E harness distinguishes three states and only accepts the first two:
`real` · `disclosed_fallback` (a hosted 503 handled correctly) · `silent_mock` (**failure**).

## 4. Live confirmation

10/10 live gates passed against the real hosted model
(`evaluation/results/final_live_ai_gates.json`), and the deployed Render instance reports
the same model with `real=True` on a live Morisyen request
(`evaluation/results/final_render_ai_check.json`).
