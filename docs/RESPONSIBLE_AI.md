# Responsible AI — Lamer Konekte

1. **Suggest, never declare.** The model proposes from a constrained candidate list; a human confirms every species before anything downstream happens. Low confidence forces manual selection.
2. **Deterministic law.** Legality never comes from the model. A versioned, source-attributed rule engine decides — and says `unknown` rather than guessing. Every result carries "Verify against the latest official fisheries notice."
3. **Honest measurements.** AI size estimates are labelled `estimated_size_unverified_cm` and are architecturally unable to reach the rule engine; only ruler-measured lengths count.
4. **No safety verdicts.** Marine data is informational; the app has no code path that outputs "safe to sail."
5. **Radical provider honesty.** Every response declares its provider mode, model, latency and `real_inference` flag; mock and fallback modes disclose themselves; "local/edge" can only appear after a real model load.
6. **Language dignity.** Morisyen is a first-class language, and provisional names are marked as provisional rather than guessed silently.
7. **Privacy floor.** In-memory images, rounded coordinates, redacted traces, resettable demo data.
8. **Honest reporting.** Blocked gates (API key, Kaggle auth) are reported as blocked — never simulated. See `docs/LIMITATIONS.md`.
