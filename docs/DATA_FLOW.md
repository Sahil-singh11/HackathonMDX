# Data Flow

```
[Fisher device: PWA]
  │ photo (multipart, ≤8MB) + note + language (+ optional rounded-later coords)
  ▼
[FastAPI /api/analyse-catch]
  ├─ quality gate (in-memory; invalid → retake, NO model call)
  ├─ candidate retrieval (local catalogue)
  ├─ provider dispatcher
  │    ├─ hosted: compressed JPEG + note + candidates → Gemini API (gemma-4-26b-a4b-it)
  │    │          ↔ function calls → allow-listed local tools (marine cache/Open-Meteo, catalogue, DB)
  │    └─ mock: deterministic local logic (no network)
  ├─ response assembly + limitation injection
  └─ SQLite: analysis metadata only (hash, scores, suggestion, provider) — never the image
  ▼
[Fisher confirms species + measured length]
  ▼
[/api/analyses/{id}/confirm] → deterministic rule engine (versioned sourced rules) → CatchRecord (coords rounded 2dp)
  ▼
[Declaration prepare → PDF → MOCK submit → demonstration receipt]

External parties: Open-Meteo (rounded coords only, attributed) · Gemini API (image+note for hosted analysis).
Nothing else leaves the device/server. Uploads are never written to disk.
```
