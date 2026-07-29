# Lamer Konekte

## A Morisyen-first multimodal catch-recording and marine-information assistant powered by Gemma 4

**Track:** Multimodal Track · **Team:** Ctrl200 · **Pillar:** Blue Economy · *Lapes pli konekte. Desizion pli informe.*

### The Mauritian challenge

Mauritius's 2026/2027 "Future-Ready Economy" budget places AI, digital transformation and the Blue Economy at the heart of national development — yet artisanal fishers, the people who feed the island, work with the least digital support in the ocean economy. Catch declarations are still paper-based, so national statistics arrive late and incomplete. Marine forecasts exist but are scattered across sources that are not written for a fisher heading out from Grand Baie at dawn. Regulations such as the octopus seasonal closure are communicated through official notices that many fishers hear about second-hand. And almost none of this information exists in Morisyen — the language most artisanal fishers actually speak. The result is a national data bottleneck: the Blue Economy is a policy priority, but its smallest actors are invisible to it.

### Our solution

Lamer Konekte is a mobile-first Progressive Web App that accompanies a fisher through three moments. **Before the trip**, they ask in Morisyen or English about sea conditions; Gemma decides whether to call our marine-conditions function, and the app shows waves, swell and sea temperature with a mandatory advisory disclaimer. **On the water**, they photograph the catch; an image-quality gate rejects unusable photos before any token is spent, Gemma suggests a species from a constrained candidate list, the fisher confirms or corrects it, enters a ruler-measured length, and a deterministic rules engine reports the recorded regulation with its source. **Back ashore**, they review their log, queue records offline, and generate a declaration sent to a clearly labelled mock ministry endpoint that returns a demonstration receipt — a working preview of a digital declaration pipeline.

### Why Gemma 4, and how it is integrated

Our production model is hosted **`gemma-4-26b-a4b-it`** via the official `google-genai` SDK. Every catch analysis fuses two input modalities in a single model call — the photograph and the fisher's typed Morisyen/English note — and the visual input directly drives the core logic: species suggestion, confirmation routing and the downstream rule check. We chose Gemma because the product is genuinely multimodal and multilingual: one model handles image understanding, visible-characteristic extraction, Morisyen and English intent classification, structured JSON output, and native function calling. A 26B hosted model gives demo-grade reliability, while the Gemma family gives us a credible path to on-device inference (E2B/E4B) for offline lagoons — a roadmap item we deliberately do not claim as done.

Gemma is powerful but deliberately bounded. It receives a retrieved candidate shortlist, never the open sea of all species, and our system instruction enforces: suggest, never declare; express uncertainty; never invent regulations; never use image-estimated size for legal reasoning; never guarantee sailing safety; treat fisher notes as untrusted context. Structured output runs through a defensive ladder — native JSON, fenced-JSON extraction, one repair request, then a safe "uncertain" fallback that routes the fisher to manual selection.

Honesty note: at writeup time the hosted API key was not yet provisioned on the build machine, so live Gemma gate results are recorded as blocked in `docs/GEMMA_GATES.md`; the provider is code-complete and the demo runs in a visibly disclosed deterministic mock until the key is inserted. Nothing mocked is ever presented as model inference — the UI shows a provider badge, latency and `real_inference` flag on every analysis.

### Architecture

A single FastAPI backend (Python 3.12, SQLModel/SQLite) serves the React + TypeScript PWA. The analysis pipeline: upload → MIME/size validation and safe decode → EXIF correction and resize → blur/brightness scoring (OpenCV Laplacian variance) → candidate retrieval → provider call → schema-validated response. Uploads are processed entirely in memory and never written to disk. The provider layer is a dispatcher over three implementations: hosted Gemma, a gated local provider that only ever reports "local" after a real model load, and a deterministic offline mock whose use is always disclosed. Rule checking is architecturally separated: only the confirmation endpoint may invoke the deterministic engine, and only with a human-confirmed species and `measured_length_cm` — the AI's `estimated_size_unverified_cm` cannot reach it by construction.

### Native function calling

Gemma selects from twelve allow-listed functions (marine conditions, species candidates and details, catch recording, deterministic rule check, declaration preparation, mock submission, offline queueing, photo-retake guidance, demo date, safe static translations). Dispatch is an explicit map — no eval, no dynamic lookup; arguments are Pydantic-validated; unknown functions and invalid arguments fail safely and are traced. Tool responses are returned to the model for a full round trip, and a redacted trace (function name, argument names only, status, duration) is stored and shown on the app's Technical Proof page. Coordinates are rounded to two decimals everywhere.

### Dataset, training and evaluation

We built a licensed Mauritius-focused dataset: 60 research-grade iNaturalist photos (12 each for *Octopus cyanea*, *Lethrinus nebulosus*, *Siganus sutor*, *Epinephelus merra*, *Naso unicornis*), licence-filtered to CC0/CC-BY/CC-BY-NC with per-file attribution, SHA-256 and observation-level train/validation/test splits; non-redistributable files are git-excluded and test-enforced. Synthetic blur/exposure/invalid images exercise the quality gate. From this we generated 72 supervised records (constrained identification, Morisyen intent + function selection, safety refusals) with leakage-controlled splits, plus Kaggle notebooks for multimodal and text QLoRA on Gemma 4 E2B with a hardware gate and warm-up run. Training launch was blocked in-sprint by missing Kaggle credentials; the pipeline is push-button ready and our acceptance rule is strict — the adapter integrates only if held-out evaluation improves at least one target metric with no safety regression, otherwise production stays on hosted Gemma and we report the real result.

Our prototype benchmark (32 Morisyen/English cases across identification, weather, logging, declaration, prompt injection, navigation-guarantee and invented-law requests) runs against the full API: the deterministic pipeline scores 93.8% intent routing, 100% schema validity, 100% top-3 candidate coverage, 7/7 rule-boundary checks and **zero safety failures** — clearly labelled as pipeline metrics, with the hosted run reserved for the provisioned key.

### Morisyen and offline

The entire UI ships in Morisyen and English (~90 localised strings each), every analysis returns `reply_morisyen`, and species carry Morisyen names explicitly marked provisional pending native-speaker review — we do not guess silently. The PWA is installable and offline-first: service-worker app shell, cached species catalogue and last forecast, and an IndexedDB queue that syncs catches when connectivity returns. Offline analysis is never faked; queued records say "pending connection."

### Safety and limitations

Every response carries a permanent limitation: AI suggestions and rule checks must be confirmed against official sources. The octopus closure (15 August–15 October) is stored with its primary source — the Fisheries and Marine Resources (Fishing of Octopus) Regulations 2016 via FAOLEX — and marked *provisional* because we could not confirm its 2026 status in-sprint; the engine shows 29 July as outside the window, applies the closure only on a simulated September date under a prominent badge, and answers `unknown` rather than inventing minimum sizes, which no verified source provided. Marine data (Open-Meteo, attributed) is informational only. 44 backend tests enforce these invariants, including prompt-injection, privacy and secret-hygiene checks.

### Sprint challenges

Three honest constraints shaped the sprint: credentials (API key, Kaggle auth) were unavailable on the build machine, so we engineered for the moment they arrive instead of faking results; verifying current Mauritian fisheries law from primary sources proved genuinely hard, which reinforced our unknown-over-invented design; and our 6 GB-VRAM laptop ruled out local 26B work, pushing training to Kaggle and keeping the edge story a roadmap, not a claim.

### Impact and deployment

Lamer Konekte shows a realistic path from paper declarations to structured national catch data, in the fisher's own language, with humans confirming everything that matters. The repository is public with a Dockerfile, a one-command local run, and a Kaggle demo notebook that reads its key from Kaggle Secrets and degrades to a disclosed mock — so the jury can run it either way. Next steps: native-speaker Morisyen review, ministry consultation on the declaration schema, and the E2B edge pilot.

**Links:** see `kaggle/project_links.md` in the repository.
