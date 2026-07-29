# Five-Minute Jury Demo — Lamer Konekte

Setup before walking in: backend running with built frontend (`uvicorn app.main:app --port 8000`), phone or narrow browser window installed as PWA, demo data reset, simulated date CLEARED, hero images ready in `data/demo/`. If the API key exists, `PROVIDER_MODE=hosted`; otherwise say "disclosed demonstration mode" once and move on confidently.

| Time | Beat | Action + line |
|---|---|---|
| 0:00–0:25 | Fisher story | "Meet a fisher leaving Grand Baie at dawn. Paper declarations, scattered forecasts, rules he hears second-hand — and none of it in Morisyen." |
| 0:25–0:50 | National bottleneck | "Multiply him by thousands: the Blue Economy is a national pillar, but its smallest actors are invisible to its data." |
| 0:50–1:15 | Why Gemma | "One Gemma 4 model — `gemma-4-26b-a4b-it` — handles the photo, the Morisyen, the structured JSON and the function calls. And the Gemma family scales down to the edge for offline lagoons." |
| 1:15–2:00 | Marine + function call | Type in Morisyen: *"Ki kalite lamer ena dan Grand Baie zordi?"* → show conditions, the disclaimer, then the **Technical Proof page**: `get_marine_conditions` in the trace with latency. |
| 2:00–3:10 | Catch flow (hero) | Upload octopus hero photo + note *"Mo'nn gagn enn ourite"* → quality badge → suggestion with confidence → **confirm species** (point out mandatory confirmation) → enter 45 cm measured → rule result. First with real date: *no closure — 29 July*. Then Demo Controls → simulated 1 Sept (point at the purple badge) → repeat confirm → **closed season, 2016 regulations source, provisional label, verify-notice**. |
| 3:10–3:50 | Log, offline, declaration | Show history; toggle airplane mode → queue a catch offline → reconnect → sync. Declaration → draft with MOCK banner → submit → demonstration receipt `MOCK-…`. "Never presented as a real government system." |
| 3:50–4:20 | Technical proof + training | Proof page: provider badge, `real_inference` flag, allow-listed functions, redacted trace. "Training pipeline is push-button on Kaggle — we report its real status, not a wish." |
| 4:20–4:45 | Morisyen | Flip the language switch — entire UI in Morisyen; provisional species names marked; 32-case benchmark, zero safety failures. |
| 4:45–5:00 | Impact + limitation | "From paper to structured national data, in the fisher's language, with humans confirming everything that matters. Suggestions and rules must still be verified with official sources — the app says so on every screen." |

Rehearsal rule: run the whole script twice against mock mode; it must work with WiFi off (except marine live fetch, which falls back to cache/mock visibly).
