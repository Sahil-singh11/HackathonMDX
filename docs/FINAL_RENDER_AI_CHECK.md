# Final Render AI Check

Run 2026-07-29T23:58:24.136425+00:00 · `https://lamer-konekte.onrender.com`

**Reachable: YES** (first 200 after 3750 ms) · 24 passed · 0 failed · 0 skipped

| Check | Result | Detail |
|---|---|---|
| deployment reachable (after cold start) | PASS | 3750 ms to first 200 |
| health endpoint 200 | PASS | {"status":"ok","service":"lamer-konekte"} |
| homepage responds | PASS | 200, 809 bytes |
| homepage is the PWA (not a stack trace) | PASS | branded HTML served |
| provider-status endpoint responds | PASS | 200 |
| production model reported | PASS | gemma-4-26b-a4b-it |
| hosted configured on the server (key present remotely) | PASS | True |
| default provider mode is hosted | PASS | hosted |
| mock is labelled simulated (not shown as real) | PASS | capability surface present |
| experimental E2B not enabled/advertised | PASS |  |
| no secret in status response | PASS |  |
| frozen API contract present | PASS | 25 paths |
| no adapter/router endpoint exposed | PASS |  |
| CORS configured for the frontend | PASS | status=400 allow-origin=None |
| no debug stack trace on error | PASS | 404, 34 bytes |
| live Morisyen marine request succeeded | PASS | 24297 ms |
| marine function selected | PASS | ['get_marine_conditions'] |
| real inference OR disclosed fallback | PASS | real=True disclosed=False |
| no secret in analysis response | PASS |  |
| internal diagnostics redacted | PASS |  |
| live image request succeeded | PASS | 13577 ms, quality=acceptable |
| species confirmation still required | PASS |  |
| no premature legal decision | PASS | pending_confirmation |
| mock declaration prepare labelled MOCK | PASS | MOCK DEMONSTRATION — NOT AN OFFICIAL GOVERNMENT SUBMISSION |

> Deployment status here is measured against the live URL only — no local result
> is used as evidence of deployment health.
