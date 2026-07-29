# Product Requirements — Lamer Konekte

Morisyen-first, multimodal catch-recording and marine-information assistant for Mauritius's artisanal fishers. Tagline: *Lapes pli konekte. Desizion pli informe.*

## Users
Artisanal fishers (primary), fisheries officers reviewing declarations (secondary), jury (demo).

## Three moments (functional requirements)

### M1 — Before the trip
- FR1.1 Ask in Morisyen or English for marine conditions; Gemma decides whether to call `get_marine_conditions`.
- FR1.2 Display wave height/direction/period, swell height/direction/period, SST when available, source, update time, stale/cache indicator.
- FR1.3 Mandatory disclaimer on every marine display: "Marine forecasts are informational and may be incomplete near the coast. Confirm conditions through official local marine advisories before travelling."
- FR1.4 Never state safe-to-sail/safe-to-fish/guaranteed conditions.

### M2 — On the water
- FR2.1 Photograph catch (camera or upload); optional typed note (en/mfe).
- FR2.2 Image-quality gate (blur/brightness/MIME/size) before any token spend; unusable → retake guidance.
- FR2.3 Constrained species suggestion from a retrieved candidate shortlist; visible characteristics; uncertainty label.
- FR2.4 **Mandatory** fisher confirmation or correction; low confidence forces manual selection.
- FR2.5 Measured length entry (ruler guidance); AI size estimate labelled `estimated_size_unverified_cm`, never used for legality.
- FR2.6 Deterministic rule check only after confirmation, only with `measured_length_cm`; missing data ⇒ `unknown`.

### M3 — Back ashore
- FR3.1 Catch history; today report.
- FR3.2 Declaration draft; PDF export; submit to **clearly labelled MOCK** ministry endpoint; demonstration receipt.
- FR3.3 Offline queue with sync when connected.

## Non-functional
- NFR1 Mobile-first PWA, installable, outdoor-readable, accessible (labels, contrast, large targets, reduced motion).
- NFR2 Full en/mfe localisation.
- NFR3 Mock mode fully offline; hosted→mock fallback visibly disclosed.
- NFR4 Server-side API key only; uploads deleted after analysis; no raw media in DB or logs.
- NFR5 Permanent limitation string on every analysis response: "Lamer Konekte provides AI-assisted catch documentation and informational guidance. Species suggestions and regulatory checks must be confirmed against official sources and by the fisher or an authorised officer."

## Out of scope (hackathon)
Real government integration, payment, multi-user auth, real-time vessel tracking, navigation guidance.
