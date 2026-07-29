# AI Submission Summary — Lamer Konekte (Team Ctrl200)

One page. Full evidence: `docs/AI_JUDGE_TECHNICAL_PROOF.md`.

---

## What the AI does, live

Fishers in Mauritius type in **Morisyen** (or French/English mixes) and send catch photos.
Hosted **`gemma-4-26b-a4b-it`** — real inference through the official `google-genai` SDK —
classifies intent, selects from 12 allow-listed functions (marine conditions via a real
Open-Meteo round trip, catch logging, mock declarations…), analyses catch photos against a
constrained candidate list, and returns structured, Pydantic-validated responses in
English and Morisyen. Every response requires fisher confirmation of species; legality is
decided only by a deterministic rules engine, never by the model.

## What we trained, honestly

We fine-tuned **`google/gemma-4-E2B-it`** (QLoRA 4-bit NF4, LoRA r=8 on 205 language-model
projections, 12.1 M trainable / 0.31%) on a **Kaggle Tesla T4** in **9.2 minutes**, using a
custom 338-record Morisyen instruction/routing dataset split by semantic family, with an
immutable 32-case external benchmark and a challenge set frozen before training.

Two iterations:

- **v1** exposed a specific weakness: declaration requests were missed (recall 0.455).
- **v2** attacked exactly that with 54 targeted records → declaration recall **1.000**
  internal and external, zero over-predictions.

v2 reached **85.3%** internal / **78.1%** external intent accuracy with **100% structured
validity** and **100% safety** — beating our own hosted production model (70.6%) on the
identical split and prompt, at 4× lower latency (**4.6 s** vs 18.5 s median).

## The decision that shows engineering discipline

Before training v2, we **committed acceptance gates** derived from measured production
performance. The adapter failed them — tool-selection accuracy stayed at 58.8% against a
70% bar. **Training succeeded, but the adapter did not pass the production acceptance
gate**, so it was rejected: the provider ships disabled, names its exact failing metrics,
and hosted Gemma remains production. We did not lower the threshold; we documented why the
next iteration should target the tool head.

## Numbers that matter

| | Value |
|---|---|
| Live gates on hosted Gemma (text, Morisyen, image, tools, injection) | 10/10 pass |
| Dataset | 338 records · 164 families · 3 disjoint test sets (34/32/24) |
| Leakage validators | ALL PASS (rejects even shared 4-word runs with the benchmark) |
| Tests | **306 offline + 8 live = 314 passed, 0 failed** |
| Release gate | ALL CHECKS PASSED |
| Safety across every evaluated system | 100% pass · 0 unknown-function · 0 invented rules · 0 safety guarantees |

## Where things live

- Demo: **https://lamer-konekte.onrender.com** (free tier — first load may take ~60 s)
- Training kernel: `yuvineappadu/lamer-konekte-e2b-qlora-router-v2` (Kaggle, T4)
- Repo: https://github.com/Sahil-singh11/HackathonMDX
