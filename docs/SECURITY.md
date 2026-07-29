# Security — Lamer Konekte

## Secrets
- `GEMINI_API_KEY` lives only in `.env` (gitignored) or platform/Kaggle secrets; the frontend never receives it; `/api/config/public` exposes a boolean only.
- JSON logs pass through a redaction filter (key-pattern scrubbing); tests scan tracked files for key patterns; git history scanned clean at baseline.

## Input handling
- Uploads: MIME allow-list (jpeg/png/webp), 8 MB cap, Pillow verify + safe re-decode, EXIF-normalised, processed entirely in memory (nothing written to disk), SHA-256 kept for dedupe only.
- Notes: length-capped, treated as untrusted context; system instruction + tests cover prompt injection.
- Function calling: explicit allow-list map, Pydantic argument validation, unknown functions/invalid args fail safely, no eval/exec/dynamic dispatch/arbitrary URLs/shell (test-enforced).

## Data
- Coordinates rounded to 2 dp before storage/traces; no raw media or audio in the DB; no model chain-of-thought stored; demo reset wipes all records.

## Reporting
Hackathon project — report issues via GitHub issues on the public repository.
