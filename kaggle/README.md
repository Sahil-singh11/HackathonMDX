# Kaggle Assets — Lamer Konekte

| Notebook | Purpose |
|---|---|
| `notebooks/lamer_konekte_demo.ipynb` | Public demo: quality gate → Gemma 4 constrained suggestion → confirmation → deterministic rule check → function calling; key from Kaggle Secrets (`GEMINI_API_KEY`), disclosed mock fallback without it. Validated to run top-to-bottom. |
| `notebooks/train_gemma4_qlora.ipynb` | Training Mode A — multimodal QLoRA on Gemma 4 E2B (hardware gate first). |
| `notebooks/train_gemma4_text_adapter.ipynb` | Training Mode B — text/structured QLoRA fallback. |
| `notebooks/evaluate_adapter.ipynb` | Held-out adapter evaluation vs baseline (§18E acceptance). |
| `notebooks/audio_gate.ipynb` | Honest audio-intent gate (blocked without consented recordings). |
| `notebooks/evaluation_report.ipynb` | Renders the prototype benchmark summary. |

Automation (requires an authenticated Kaggle CLI): `scripts/kaggle_push_training.sh`, `scripts/kaggle_monitor_training.sh`, `scripts/kaggle_download_outputs.sh` (PowerShell twins included). Notebooks are generated reproducibly by `kaggle/build_notebooks.py`.

> **Pushing a notebook version via the CLI drops any attached Kaggle Secret** — `kernel-metadata.json`
> has no field for secrets, so a CLI push resets the notebook's settings and the next run falls back to
> disclosed mock mode. After any CLI push, re-attach `GEMINI_API_KEY` in the browser
> (Add-ons → Secrets → tick it for this notebook) and **Save Version → Save & Run All (Commit)** so the
> published run shows real inference.

Secrets policy: keys come only from Kaggle Secrets; nothing in these notebooks prints or persists a credential. Training data uploads go to a **private** Kaggle dataset; adapter outputs are downloaded to `kaggle/outputs/` (gitignored).
