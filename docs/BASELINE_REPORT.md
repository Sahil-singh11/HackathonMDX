# Baseline Report — Prototype Benchmark Metrics

Runs on 2026-07-29 (MUT): the deterministic **mock pipeline**, the **hosted Gemma** baseline (`gemma-4-26b-a4b-it`, real inference), and a **post-tuning hosted re-run** after the prompt fixes. Full data: `evaluation/results/baseline_mock.{json,csv}`, `evaluation/results/baseline.{json,csv}`, `evaluation/results/morisyen_results.csv`.

## Post-tuning hosted results (current, ~17:15 MUT)

After the prompt fixes (few-shot intent examples, photo-state hint, compact-JSON output, tool-call guidance — commit `288639e`):

| Metric | Pre-tuning | **Post-tuning** | Mock reference |
|---|---|---|---|
| Morisyen intent accuracy | 81.2% | **96.9%** (31/32) | 93.8% |
| Safety failures (negation-aware scorer) | 0 | **0** | 0 |
| Schema validity | 100% | **100%** | 100% |
| Weather → `get_marine_conditions` | inconsistent | **yes** | yes |
| Median latency | 21.6 s | 21.7 s (unchanged — hidden thinking tokens dominate; see note) | ~0 |

The tuned hosted model now **outperforms the deterministic keyword router** on intent (96.9% vs 93.8%). The single remaining miss (`mfe-08`: an *image* + "anrezistre sa lapes la") is genuinely ambiguous between `identify_catch` and `log_catch` — the app flow handles both identically (analyse → confirm → record), so it has no user-facing impact.

**Engineering note (learned the hard way):** do not set `max_output_tokens` on this model — it spends hidden thinking tokens before visible output, and a cap can consume the whole budget and return empty text (`finish_reason=MAX_TOKENS`, len 0). Latency is a tier/model property (~20 s median); it is handled by UX (staged progress) rather than by output caps.

## First-run headline comparison (pre-tuning, kept for the record)

| Metric | Mock pipeline | Hosted Gemma (real) | Reading |
|---|---|---|---|
| Morisyen intent accuracy (32 cases) | 93.8% | **81.2%** | Mock wins on its own keyword rules; Gemma's 6 misses all defaulted to `identify_catch` on text-only notes — see "Actionable findings". |
| Structured-output schema validity | 100% | **100%** | Every hosted response parsed into the frozen contract. |
| Safety failures | 0 | **0** (see note) | The recorded "1" is a scorer artifact: Gemma replied *"I cannot guarantee sea conditions. Please check official weather advisories"* — the correct refusal — and the naive scorer flagged the word "guarantee". Verified by manual reproduction; scorer fixed (negation-aware) for future runs. |
| Species agreement (note-expected subset) | 100% | 25% (artifact — see below) | **Not a model failure.** These cases pair a Morisyen note ("mo'nn gagn enn ourite") with a *synthetic test drawing*, not a real octopus photo. The mock parrots the note's keyword; Gemma actually looks at the image, sees no octopus, and declines to confirm — which is exactly the grounded behaviour we want. |
| Median latency | ~0 ms | **21.6 s** | Real constraint on this key tier; drives the frontend latency-UX work and the `max_output_tokens` tuning task. |
| Image-quality gate (7 checks) | 7/7 | 7/7 | Deterministic — identical by design. |
| Rule boundaries / hallucinated-rule rate | 7/7 · 0.0 | 7/7 · 0.0 | Deterministic — the model cannot touch rule decisions. |
| Weather note triggers `get_marine_conditions` | yes | not in this probe | Non-deterministic tool use when no location is given; a separate manual test *did* complete the full round trip (see `docs/GEMMA_GATES.md`). Few-shot fix assigned. |

## Live-inference evidence (manual, same day)
- Octopus hero photo → `octopus_cyanea`, high confidence, grounded characteristics ("bulbous mantle, mottled skin, arms with suckers"), Morisyen reply requesting confirmation + measured length.
- Grand Baie weather question (Morisyen) → `get_marine_conditions` called with validated args → live Open-Meteo data synthesised into a Morisyen answer including an unprompted official-advisories caution.

## Actionable findings (owned in docs/TEAM_NEXT_STEPS.md)
1. **Intent misses (6/32)** — all text-only notes misread as `identify_catch` (`mfe-08/09/11/18/24/26`): the system instruction is identification-centric. Fix: 2–3 few-shot intent examples + "no image attached" hint in the user prompt. Owner: Yuvine.
2. **Latency** — median 21.6 s. Fixes: `max_output_tokens=300`, "keep replies under 40 words" instruction, staged progress UI. Owners: Yuvine (backend), Sahil (UX).
3. **Tool-call consistency** — add one few-shot example of a location-less weather question calling the tool with fallback coordinates. Owner: Yuvine.
4. **Real image benchmark** — species agreement must be measured on the 60-image licensed set (real photos), not the synthetic-drawing cases; those measure note-grounding, not vision. Follow-up script if time allows. Owner: Dhanesh.

## Honesty notes
- Mock numbers measure the deterministic pipeline, not model quality; hosted numbers are single-run and subject to sampling variance.
- The species-agreement and safety-failure caveats above were verified by direct reproduction before being called artifacts.
