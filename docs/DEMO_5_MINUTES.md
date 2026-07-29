# Five-Minute Jury Demo — Lamer Konekte

## Setup (do this 10 minutes before, not at the podium)

1. **Warm the public URL**: open https://lamer-konekte.onrender.com once — the free tier sleeps, and a cold start costs ~30–60 s. Keep the tab open.
2. **Use a fresh/incognito window** so no old service worker serves a stale build.
3. **Seed demo data** so History and Declaration are not empty:
   `backend/.venv/bin/python backend/scripts/seed_demo_catches.py --base-url https://lamer-konekte.onrender.com`
4. **Clear the simulated date** (Demo controls → Reset) — the closure demo depends on starting from the real date.
5. Have the octopus hero photo ready to upload (`data/demo/octopus_cyanea_151112387.jpg`) — on the demo phone/laptop, not just in the repo.
6. Decide the driver and speaker per `docs/SPEAKING_ASSIGNMENTS.md`. **The speaker never drives.**

## ⚠️ Latency reality — rehearse around it

Real Gemma calls take **~20 seconds** (hidden thinking tokens; not something we can switch off on this tier). The script below spends **exactly two** model calls, each covered by narration. Never plan a third live call — if a judge asks for one, run it while answering their question, or switch to mock mode and *say so*.

## Navigation (after the redesign)

Desktop shows a **left side-nav**; narrow/mobile shows the **bottom bar**. Both carry: Home · Sea conditions · Record a catch · Catch log · Declaration. Technical proof, Demo controls, Privacy and About are reached from the **dashboard tiles**.

| Time | Beat | Action + line |
|---|---|---|
| 0:00–0:25 | Fisher story | "Meet a fisher leaving Grand Baie at dawn. Paper declarations, scattered forecasts, rules he hears second-hand — and none of it in Morisyen." |
| 0:25–0:50 | National bottleneck | "Multiply him by thousands: the Blue Economy is a national pillar, but its smallest actors are invisible to its data." |
| 0:50–1:15 | Why Gemma | "One Gemma 4 model — `gemma-4-26b-a4b-it` — handles the photo, the Morisyen, the structured JSON and the function calls. And the Gemma family scales down to the edge for offline lagoons." |
| 1:15–2:00 | Marine + function call (**model call #1**) | Type in Morisyen: *"Ki kalite lamer ena dan Grand Baie zordi?"* → **while it thinks (~20 s), narrate**: "one model is reading Morisyen, deciding a tool is needed, and calling our marine function." → show conditions + the mandatory disclaimer → **Technical proof** tile: `get_marine_conditions` in the trace with its latency. |
| 2:00–3:10 | Catch flow (**model call #2**) | Upload the octopus hero photo + note *"Mo'nn gagn enn ourite"* → quality badge appears instantly (**say: "no tokens spent on unusable photos"**) → **while it thinks, narrate the constraint**: "it only ever chooses from a retrieved shortlist" → suggestion + confidence + visible characteristics → **confirm species** (stress: mandatory, the fisher decides) → enter 45 cm → rule result on the real date. Then **Demo controls → set 2026-09-01** (point at the purple SIMULATED DATE badge) → confirm again → **closed season, GN 167/2016, provisional, verify-notice**. No new model call is needed for the second rule check. |
| 3:10–3:50 | Log, offline, declaration | Show history; toggle airplane mode → queue a catch offline → reconnect → sync. Declaration → draft with MOCK banner → submit → demonstration receipt `MOCK-…`. "Never presented as a real government system." |
| 3:50–4:20 | Technical proof + training | Proof page: provider badge, `real_inference` flag, allow-listed functions, redacted trace. "Training pipeline is push-button on Kaggle — we report its real status, not a wish." |
| 4:20–4:45 | Morisyen | Flip the language switch — entire UI in Morisyen; provisional species names marked; 32-case benchmark, zero safety failures. |
| 4:45–5:00 | Impact + limitation | "From paper to structured national data, in the fisher's language, with humans confirming everything that matters. Suggestions and rules must still be verified with official sources — the app says so on every screen." |

## Optional 20-second add-on if the mantle question comes up

After the rule result, mention: *"We read the actual gazette. GN 167/2016 also bans octopus under 7 cm — but measured by **mantle**, not total length. Our app records total length, so instead of comparing the wrong numbers it returns `unknown` and tells the fisher to measure the mantle."* This is our strongest trust moment; keep it in the pocket for Q&A if time is tight.

## Rehearsal rules

- Run the whole script **twice with a timer**, on the real deployed URL, at real latency.
- Then run it once with WiFi off to prove the offline queue and cached shell (marine falls back visibly to cache/mock).
- If a rehearsal overruns 5:00, cut the Technical-proof detour first — never the confirmation step or the disclaimers.
