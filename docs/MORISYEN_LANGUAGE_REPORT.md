# Morisyen Language Report

## What is localised
Complete en/mfe dictionaries (`frontend/src/i18n/{en,mfe}.json`, ~90 keys each): navigation, photo guidance, quality warnings, species confirmation, measurement guidance, marine summary + disclaimer, catch log, declaration (incl. MOCK warning), privacy, offline states, errors, static safety warnings. Backend static safety strings are served bilingually via the `translate_safe_static_message` tool; every analysis response carries `reply` (en) and `reply_morisyen` (mfe).

## Evaluation
32 cases in `evaluation/cases/morisyen_cases.json` covering: identification, logging, weather, declaration, unknown size, uncertainty, blurry photo, offline use, octopus closure, prompt injection, mixed languages, navigation-guarantee requests, invented-legal-advice requests. Results: `evaluation/results/morisyen_results.csv` (mock pipeline: 93.8% intent, 0 safety failures — see `docs/BASELINE_REPORT.md` for the honesty note).

## Orthography approach
Kreol Morisien in the spirit of the Grafi-larmoni-based standard (e.g. *lapes*, *lamer*, *anrezistre*, *lespes*, *konfidansialite*). No French-orthography mixing in UI strings except species names where the local usage is French-derived.

## Known limitations
- Species Morisyen names are **provisional** (see `research/SPECIES_NAME_REGISTER.md`) and are displayed with an asterisk + English/scientific names.
- All critical static wording requires native-speaker review before public claims of correctness — see `docs/MORISYEN_HUMAN_REVIEW.md`.
- Model-generated Morisyen (hosted mode) is untested until the API key exists.
