# Final Local AI End-to-End Report

Run 2026-07-29T22:40:07.167523+00:00 · `http://127.0.0.1:8011` · provider `hosted` · **7/7 flows passed**

> API layer automated. **Browser rendering was not automated** — the manual steps
> are in `docs/AI_USER_TEST_GUIDE.md`. No browser step is claimed as passed here.

| Flow | Description | Steps | Result |
|---|---|---|---|
| `preflight` | API reachable, production model reported | 7/7 | **PASS** |
| `A_marine_conditions` | Morisyen -> Gemma function selection -> validated args -> real Open-Meteo -> disclaimer | 9/9 | **PASS** |
| `B_catch_analysis` | image -> quality gate -> candidates -> Gemma -> suggestion + mandatory confirmation | 8/8 | **PASS** |
| `C_confirmed_catch` | confirmed species + measured length -> deterministic rules -> recorded | 5/5 | **PASS** |
| `D_declaration` | prepare -> PDF -> clearly labelled MOCK submission + receipt | 6/6 | **PASS** |
| `E_offline_queue` | queue -> visible -> sync -> duplicate prevented | 4/4 | **PASS** |
| `F_technical_proof` | trace exposes provider/model/real_inference/function/latency/safety, redacted | 10/10 | **PASS** |

## Failed steps

None.
