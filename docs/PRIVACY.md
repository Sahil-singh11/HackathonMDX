# Privacy — Lamer Konekte

- **Photos**: analysed in memory, sent (compressed) to the hosted model only for the analysis call, never stored server-side; only a content hash is retained for duplicate detection.
- **Location**: optional; user-initiated; rounded to ~1 km (2 decimal places) before any storage or trace; precise coordinates are never logged or displayed.
- **Audio**: no recording exists in the product today; any future recording requires explicit consent and is never committed to the repository.
- **Profile**: name and fishing area are optional, stored locally (browser) and in demo records only.
- **Model data**: no chain-of-thought stored; tool traces record function names, argument names, status and duration only.
- **Reset**: `POST /api/demo/reset` deletes all catches, analyses, declarations, queue items and traces.
- **Third parties**: Open-Meteo receives rounded coordinates for forecasts (no account, attributed); Google's Gemini API receives the compressed image + note for hosted analysis under its API terms.
