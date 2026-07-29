# Demo Failure Recovery

| Failure | Symptom | Recovery (rehearsed) |
|---|---|---|
| Hosted API down/slow | Analysis > 10 s or error | The dispatcher auto-falls back to mock with a visible disclosure — narrate it as a feature: "offline resilience by design." |
| No API key at demo time | Provider badge shows mock | Say once: "demonstration mode — the hosted path is identical code, gated on credentials." Show the Technical Proof page honestly. |
| Venue WiFi dead | Marine fetch fails | Cached/stale badge appears, or deterministic mock values; PWA shell is precached. Whole flow works offline. |
| Backend crash | UI errors | `cd backend && .venv/bin/uvicorn app.main:app --port 8000` (< 10 s); demo data reseeds via Demo Controls. |
| Laptop dies | — | Backup phone with the PWA installed against the deployed URL (if live) + screen recording in `presentation/assets/` + screenshots in slides. |
| Projector refuses phone | — | Browser at 420 px width on the laptop — identical UI. |
| Wrong demo date left set | Purple badge visible | Demo Controls → Reset. The badge existing is itself a talking point. |
| Judge asks to try their photo | Unknown species | Expected behaviour: low confidence, manual selection path — narrate the safety design. |
