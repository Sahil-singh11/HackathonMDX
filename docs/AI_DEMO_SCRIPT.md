# AI Demo Script

Three demos, then a 60–75 s spoken script. Everything shown is real inference — no demo
uses the mock unless the fallback banner is deliberately being shown.

Pre-demo checklist: backend up with `GEMINI_API_KEY` set (`provider_mode=hosted`),
https://lamer-konekte.onrender.com warmed (free tier sleeps — open it 2 min early), the
Kaggle kernel page and `training/results/training_history.csv` chart open in tabs.

---

## DEMO A — Real hosted model, Morisyen → tool round trip (~25 s)

1. Type in Morisyen: **“Ki kondisyon lamer pou dime dan Flic-en-Flac?”**
2. Show the response and then the **function-call trace** in the UI/API payload:
   - Gemma requested `get_marine_conditions` with derived Flic-en-Flac coordinates —
     it was never given them;
   - arguments passed **Pydantic validation** before execution;
   - a **real Open-Meteo** result came back and Gemma folded it into the answer;
   - the reply carries the marine disclaimer and never says conditions are "safe".
3. One line to say: *"That's live Gemma 4 26B doing native function calling from Mauritian
   Creole, with every argument validated server-side before anything executes."*

## DEMO B — Real multimodal model, catch photo (~25 s)

1. Upload a demo catch photo (`data/demo/epinephelus_merra_*.jpg`).
2. Show: species **suggestion** constrained to the candidate shortlist, with visible
   characteristics and stated uncertainty — never an authoritative ID.
3. Tap **confirm species**, enter a measured length → the **deterministic rules engine**
   returns the legal check. Point out: the model never decides legality, and a
   photo-estimated size is labelled unverified.

## DEMO C — Training evidence (~20 s)

Open the Kaggle kernel (`lamer-konekte-e2b-qlora-router-v2`, Tesla T4) and show:

- the QLoRA notebook and the **training curve** (eval loss 0.088 → 0.058, 9.2 min, 9.2 GiB);
- the **48 MB adapter** (12.1 M trainable params, 0.31%);
- the v1→v2 board: intent 73.5%→**85.3%**, declaration recall 0.455→**1.000**;
- latency: trained router **4.6 s** vs hosted 18.5 s;
- and the punchline: the **frozen acceptance gate rejected it anyway** (tool accuracy
  58.8% vs 70%) — the thresholds were committed before training and never moved.

---

## Spoken script (60–75 seconds)

> “Fishers here speak Morisyen, so that's where we start. *[types]* ‘Ki kondisyon lamer
> pou dime dan Flic-en-Flac?’ — this is live Gemma 4, twenty-six billion parameters,
> and watch the trace: it chose the marine-conditions function itself, our backend
> validated the arguments, called the real Open-Meteo API, and Gemma wrote the answer in
> Creole — with a disclaimer, because this app never guarantees the sea is safe.
>
> *[uploads photo]* Same model, real vision: it suggests a species only from our
> catalogue, says what it can actually see, and makes the fisher confirm. Legality is
> never the model's call — a deterministic rules engine does that, after a real
> measurement.
>
> And we didn't stop at prompting. We built a 338-record Morisyen routing dataset and
> QLoRA-trained Gemma 4 E2B on a Kaggle T4 — nine minutes, forty-eight megabytes of
> adapter. Version one missed declarations; we targeted exactly that, and version two
> got every single one — 85% intent accuracy, four times faster than hosted.
>
> Then it hit the acceptance gate we'd committed *before* training — tool selection was
> below the bar — so we rejected our own adapter and kept hosted Gemma in production.
> Training succeeded; the adapter didn't pass the gate. That's the discipline we'd want
> in software that talks to fishers about the sea.”

Timing guide: A ≈ 25 s · B ≈ 20 s · C ≈ 25 s. Cut line if over: the adapter-size sentence.

## If something breaks live

- Hosted 503 (model under load): the app falls back to the **clearly-labelled** mock —
  show the disclosure banner and say so; do not present it as inference.
- Render cold start: keep the local backend as DEMO A/B fallback.
