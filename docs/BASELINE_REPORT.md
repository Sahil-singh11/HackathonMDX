# Baseline Report — Prototype Benchmark Metrics

Run: 2026-07-29 (MUT) · Provider: **mock (deterministic pipeline)** · Full data: `evaluation/results/baseline_mock.{json,csv}`, `evaluation/results/morisyen_results.csv`.

## Honesty note (read first)
The hosted Gemma baseline (18A of the brief) **could not run at baseline time because no `GEMINI_API_KEY` is configured**. The numbers below measure the deterministic pipeline in mock mode — safety rails, schema validity, image-quality gate, rule engine, retrieval and keyword intent routing. They are **not** Gemma model-quality numbers. Re-run `evaluation/run_all.py --provider hosted` the moment the key exists; results will land in `evaluation/results/baseline.{json,csv}`.

## Results (mock pipeline)

| Group | Metric | Value |
|---|---|---|
| Morisyen (32 cases) | intent accuracy | **93.8%** (30/32) |
| | species agreement (where expected) | 100% |
| | structured-output schema validity | 100% |
| | safety failures (legality claims, key leaks, guarantee language, invented rules, missing mock disclosure) | **0** |
| Image quality (7 checks) | correct classifications | 7/7 (incl. invalid-MIME) |
| Species shortlist (5 probes) | top-1 / top-3 coverage | 100% / 100% |
| Rule boundaries (7 checks) | correct (incl. 29-Jul-not-closed, Aug-15/Oct-15 boundaries, Feb historical-rule ignored) | 7/7 |
| | hallucinated-rule rate | 0.0 |
| Function calling | Morisyen weather note triggers `get_marine_conditions` with ok status | yes |
| Offline queue | enqueue + process | 1 processed, 0 failed |

## Failed cases (mock keyword router limitations — expected)
- `mfe-09` "Met sa dan mo zistwar lapes." — expected `log_catch`, got `other` (phrase not in the keyword list).
- `mfe-15` offline question — expected `other`, got `weather_query` ("lamer" keyword collision).

These are precisely the cases where real Gemma inference should outperform the keyword router; they are part of the hosted-vs-mock comparison once the key exists.

## Metrics the hosted run will add
Top-1/top-3 species agreement on real photos (60-image licensed set), correct-uncertainty rate, false-confident errors, Morisyen intent via real inference, function selection + argument validity from the model, hallucinated-rule rate under adversarial prompts, latency distribution, API failure rate.
