# Baseline Environment Report — Lamer Konekte (Team Ctrl200)

Captured: 2026-07-29 14:26 Mauritius time (+04) on the primary dev machine (WSL2 Ubuntu 22.04 on the Windows laptop).

## Repository

| Item | Value |
|---|---|
| Path | `/home/yad/HackathonMDX` |
| Branch | `main` (clean) |
| History | 1 commit (`db7ccb2 Initial commit`) — README only |
| Remote | `https://github.com/Sahil-singh11/HackathonMDX` |
| Visibility | PRIVATE (per team; must become PUBLIC before final submission) |
| `.gitignore` | Created in this session (secrets, media, weights, DBs excluded) |
| Secret scan | Working tree + full git history scanned — **clean** |

## Toolchain

| Tool | Status |
|---|---|
| Python | 3.12.13 available (`python3.12`); system default 3.10.12 |
| pip | 26.1.2 |
| Node.js / npm | v20.20.2 / 10.8.2 |
| Git | 2.34.1 |
| GitHub CLI | 2.4.0, **authenticated** (user YadhavRamsahye) |
| Kaggle CLI | **NOT installed / NOT authenticated** — blocker for Kaggle automation |
| Docker | 29.1.3 present |
| NVIDIA GPU | RTX 3060 Laptop, 6144 MiB VRAM, driver 592.00, visible in WSL via `nvidia-smi` |
| WSL RAM | 7.4 GiB allocated to WSL (of 16 GiB laptop); ~4.7 GiB available |
| Disk | ~209 GiB free on WSL vdisk |

> WSL note: the execution prompt describes the Windows host (16 GB RAM). The WSL VM only sees ~7.4 GB. Local model experiments must budget against the **WSL** limit, which makes even E2B 4-bit tight; treat local edge as P3 and prefer Kaggle for anything heavy.

## Credentials (presence only — no values inspected)

| Credential | Present |
|---|---|
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | **NO** — blocks all real hosted Gemma calls |
| Kaggle (`~/.kaggle/kaggle.json`, env vars) | **NO** — blocks Kaggle dataset/notebook push and GPU training |
| Hugging Face token | **NO** — blocks gated Gemma model downloads (licence acceptance also required) |
| `.env` in repo | Not present (good); `.env.example` created |

## Connectivity (HTTP status at capture time)

| Endpoint | Result |
|---|---|
| `generativelanguage.googleapis.com` | Reachable (404 on bare root = server up) |
| `kaggle.com` | 200 |
| `huggingface.co` | 200 |
| Open-Meteo Marine API (Mauritius coords) | 200 with data |
| iNaturalist API | 200 |

## Time budget

- System clock: 2026-07-29 14:26 MUT.
- Hackathon start not recorded anywhere in the repo. **Assumption (documented):** start ≈ repo creation today 13:36 MUT, so deadline ≈ **2026-07-30 13:36 MUT**.
- Major-feature freeze: **2026-07-30 10:36 MUT** (3 h before deadline).
- Final submission verification: **2026-07-30 12:36 MUT** (1 h before deadline).
- The team must correct these times in `docs/TIMEBOX.md` if the official deadline differs.

## Blocking human actions identified at baseline

1. Insert `GEMINI_API_KEY` into `/home/yad/HackathonMDX/.env` (copy `.env.example`). Without it, hosted Gemma gates cannot run; the app runs in clearly-disclosed mock mode.
2. Install + authenticate Kaggle CLI (`pip install kaggle`, place `kaggle.json`) to enable training automation.
3. (Optional, P3) Hugging Face login + Gemma licence acceptance for local edge tests.
4. Final Kaggle Writeup submission is manual.
