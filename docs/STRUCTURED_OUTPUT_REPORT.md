# Structured Output Report — AI Step 2

Run: 2026-07-29T14:56:38.523039+00:00 → 2026-07-29T14:59:03.642342+00:00  
Model: `gemma-4-26b-a4b-it` · SDK: `google-genai` 2.14.0 · Python 3.12.2  
Cases per configuration: **22**

> synthetic/redistributable inputs only; no prompt text, image bytes, model prose or chain of thought stored

## Unsupported configurations

- **Config D** — `response_format` is not a field of GenerateContentConfig in google-genai 2.14.0 (verified by model_fields introspection). Config D was NOT run and has no fabricated result.

## Comparison

| Metric | A — control_prompt_json_coercion | B — native_json_schema_minimal | C — native_json_schema_high_thinking | E — prompt_json_minimal_compact | F — prompt_json_minimal_full_prompt |
|---|---|---|---|---|---|
| Requests | 22 | 22 | 22 | 22 | 22 |
| API failure rate | 0.0% | 4.5% | 0.0% | 0.0% | 0.0% |
| Raw JSON parse rate | 100.0% | 59.1% | 45.5% | 100.0% | 100.0% |
| Native schema-valid rate | 13.6% | 54.5% | 36.4% | 22.7% | 22.7% |
| **Exact enum-valid rate** | 100.0% | 59.1% | 45.5% | 100.0% | 100.0% |
| Coercion rate (any) | 86.4% | 9.1% | 13.6% | 77.3% | 77.3% |
| **Enum coercion rate** | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Repair rate | 0.0% | 36.4% | 54.5% | 0.0% | 0.0% |
| Final schema-valid rate | 100.0% | 72.7% | 59.1% | 100.0% | 100.0% |
| Safety pass rate | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Intent accuracy | 100.0% | 70.0% | 87.5% | 53.8% | 100.0% |
| SDK `parsed` populated | 0.0% | 59.1% | 45.5% | 0.0% | 0.0% |
| Avg output tokens | 200 | 476 | 517 | 187 | 203 |
| Avg thought tokens | — | — | — | — | — |
| Latency avg | 5825 ms | 18693 ms | 34806 ms | 7743 ms | 6541 ms |
| Latency median | 4648 ms | 5233 ms | 28007 ms | 4859 ms | 5812 ms |
| Latency p90 | 8250 ms | 53530 ms | 64139 ms | 8421 ms | 9093 ms |
| Median latency — text only | 4515 ms | 26038 ms | 47242 ms | 4546 ms | 4913 ms |
| Median latency — image | 7305 ms | 4796 ms | 8007 ms | 6835 ms | 7382 ms |

## Per-configuration notes

- **A — `control_prompt_json_coercion`**: Step-1 control: JSON asked for in the prompt, coercion at the boundary.
- **B — `native_json_schema_minimal`**: response_mime_type + response_json_schema, MINIMAL thinking, compact prompt.
- **C — `native_json_schema_high_thinking`**: Same schema and prompt as B, HIGH thinking.
- **E — `prompt_json_minimal_compact`**: Prompt-instructed JSON + MINIMAL thinking + compact prompt; coercion at the boundary.
- **F — `prompt_json_minimal_full_prompt`**: Control mechanism + full prompt + MINIMAL thinking.

## Per-group final schema validity

| Group | A | B | C | E | F |
|---|---|---|---|---|---|
| declaration_intent | 100.0% | 100.0% | 50.0% | 100.0% | 100.0% |
| english_catch_registration | 100.0% | 50.0% | 0.0% | 100.0% | 100.0% |
| image_plus_morisyen | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| image_species_suggestion | 100.0% | 66.7% | 100.0% | 100.0% | 100.0% |
| low_quality_image | 100.0% | 100.0% | 66.7% | 100.0% | 100.0% |
| missing_information | 100.0% | 100.0% | 50.0% | 100.0% | 100.0% |
| morisyen_catch_registration | 100.0% | 50.0% | 50.0% | 100.0% | 100.0% |
| prompt_injection | 100.0% | 0.0% | 50.0% | 100.0% | 100.0% |
| unknown_species | 100.0% | 50.0% | 50.0% | 100.0% | 100.0% |
| weather_intent | 100.0% | 100.0% | 50.0% | 100.0% | 100.0% |

## Coercion transparency

A coerced result is never reported as natively schema-compliant: `native_schema_valid` and `coercion_applied` are recorded separately for every request, with the changed fields listed in `coercion_fields`.

| Coerced field | Times |
|---|---|

