# Architecture — Lamer Konekte

Single monorepo, no microservices.

```
React PWA (Vite, TS)  ──HTTP──▶  FastAPI backend  ──▶  SQLite (SQLModel)
  i18n en/mfe                      │
  IndexedDB offline queue          ├─ providers/   hosted (google-genai, gemma-4-26b-a4b-it)
  service worker                   │               local (gated; only after real load)
                                   │               mock  (deterministic, offline, disclosed)
                                   ├─ tools/       allow-listed function registry (12 fns)
                                   ├─ services/    vision quality · species retrieval ·
                                   │               fisheries_rules (deterministic) ·
                                   │               marine (Open-Meteo + cache) ·
                                   │               catches · declarations (PDF) · sync
                                   └─ storage/     temp uploads (deleted after analysis)
```

## Request flow: POST /api/analyse-catch
1. Validate multipart (MIME, size), decode safely, EXIF-correct, resize.
2. Vision quality service: blur (Laplacian variance), brightness, glare/exposure warnings. `invalid` ⇒ return retake response, **no model call**.
3. Species retrieval: candidate shortlist from the catalogue (never the whole catalogue, never free identification).
4. Provider (hosted/local/mock) called with system instruction + candidates + image + untrusted note. Native structured output; JSON retry → repair → safe uncertain fallback.
5. Function calling: model may request an allow-listed function; Pydantic-validated args; explicit function map (no dynamic dispatch); tool response returned to the model; redacted trace stored.
6. Response assembled per frozen contract; limitation string injected server-side; analysis persisted; temp image deleted.

## Confirmation flow: POST /api/analyses/{id}/confirm
Only here does the deterministic rule engine run — with the confirmed species and `measured_length_cm` only. Missing measurement or unverified rule ⇒ `unknown`. Result stored on the catch record with rule source attribution.

## Key invariants (enforced in code + tests)
- Rule check impossible before confirmation (endpoint separation).
- `estimated_size_unverified_cm` never reaches the rule engine.
- Mock never claims `real_inference: true`.
- Provider fallback hosted→mock sets `mode: "mock"` and a visible disclosure.
- Coordinates rounded to 2 dp in traces; precise values never logged.

## Database entities
CatchAnalysis, CatchRecord, LedgerEntry, MarineForecastCache, Declaration, SyncQueueItem, ToolTrace, DemoSetting. No API keys, no raw audio, no model reasoning, minimal metadata only.

`FisherProfile`, `Species` and `SpeciesRule` were removed on 2026-07-29 (DECISION_LOG 12): they were created but never read. **Species and fisheries rules are read from versioned JSON under `data/`, never from the database** — `data/processed/species_catalogue.json` via `services/species/retrieval.py` and `data/rules/species_rules.json` via `services/fisheries_rules/engine.py`. That JSON carries the source attribution and `verification_status` the rule engine and the offline assistant both depend on, which is why it is the source of truth.
