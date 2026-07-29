# Project Links — Lamer Konekte (Team Ctrl200)

| Item | Link | Status |
|---|---|---|
| Public code repository | https://github.com/Sahil-singh11/HackathonMDX | **PRIVATE until the public-release gate passes** — flip via `scripts/make_repo_public.sh` |
| Public demo URL | **https://lamer-konekte.onrender.com** | LIVE (Render free tier, Frankfurt). Validated 29 Jul: health, PWA, real hosted Gemma inference, no key in bundle. Free tier sleeps when idle — first load ~30–60 s. |
| Kaggle demo notebook | **https://www.kaggle.com/code/yuvineappadu/lamer-konekte-gemma-4-demo-team-ctrl200** | PUBLIC, pushed 29 Jul. Pending: attach `GEMINI_API_KEY` secret (in browser, logged in as yuvineappadu) → Run All → Save Version for a real-inference output. |
| Training notebooks | `kaggle/notebooks/train_gemma4_qlora.ipynb`, `train_gemma4_text_adapter.ipynb` | Push with `scripts/kaggle_push_training.sh` once Kaggle CLI is authenticated |
| Evaluation results | `evaluation/results/` in the repo | Mock-pipeline baseline committed |
| Release tag | `hackathon-submission-v1` | Created at public release |

Update this file with real URLs before final submission — the checklist blocks submission while any row says pending.
