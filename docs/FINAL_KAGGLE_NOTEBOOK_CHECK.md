# Final Kaggle Notebook Check

Notebook: `kaggle/notebooks/lamer_konekte_demo.ipynb`
Kaggle: https://www.kaggle.com/code/yuvineappadu/lamer-konekte-gemma-4-demo-team-ctrl200
Status via Kaggle API: **COMPLETE** (no failure message) · version **8** pushed 2026-07-30.

Generated from `kaggle/build_notebooks.py` (source of truth — edit the builder, not the
`.ipynb`).

---

## 1. Audit result

| Requirement | Result |
|---|---|
| Runs top to bottom | PASS — 9 cells, **0 syntax errors**; last cell executed locally to confirm it renders |
| Reads `GEMINI_API_KEY` from Kaggle Secrets | PASS — `UserSecretsClient().get_secret(...)` |
| Never prints the secret | PASS — no `print()` of the key; degrades to disclosed mock when absent |
| Uses the exact production model | PASS — `gemma-4-26b-a4b-it` |
| Demonstrates real text inference | PASS |
| Demonstrates Morisyen | PASS |
| Demonstrates image input | PASS — real licensed iNaturalist catch photo embedded |
| Demonstrates structured output | PASS — frozen contract fields incl. `species_confirmation_required` |
| Demonstrates function selection | PASS — `get_marine_conditions` |
| Demonstrates the tool round trip | PASS — `from_function_response` |
| Shows the marine disclaimer | PASS |
| Requires species confirmation | PASS — mandatory confirm step before any rule check |
| Labels ministry submission as mock | PASS — `MOCK` label present |
| **Includes real QLoRA evidence** | **PASS (added in v8)** |
| **Reports the rejected adapter honestly** | **PASS (added in v8)** |
| Fallback fixtures redistributable | PASS — CC-BY iNaturalist photo with attribution + synthetic generated images |
| No local Windows paths | PASS |
| No placeholder URLs / TODOs | PASS |

## 2. Gap found and fixed

The demo notebook predated Steps 3–4, so it contained **no training evidence and no mention
of the adapter decision** — a documentation mismatch against the submission claims. Added a
`DEMO_TRAINING` cell to the builder (and two outro bullets) that print, from committed
artifacts:

- production vs fine-tuning model, QLoRA method, LoRA targeting **language-model layers only**,
  Kaggle Tesla T4, 12 079 104 trainable params (0.31%), 552 s, 9.21 GiB, best val loss 0.0577,
  48.4 MB adapter;
- dataset 338 / 164 families and the **three separate** test sets (34 / 32 / 24);
- a v1→v2 comparison table with the hosted-26B reference column;
- the pre-registered gate outcomes and:

> Training succeeded, but the adapter did not pass the production acceptance gate.

- the targeted win (`make_declaration` 45.5% → 100% internal/external, 72.7% on unseen
  challenge families).

The notebook states plainly that the adapter ships **disabled** and hosted Gemma 4 26B
remains production. Nothing in it describes the adapter as production.

## 3. Remaining browser-only actions (cannot be automated)

1. **Attach the `GEMINI_API_KEY` secret** — open the notebook logged in as `yuvineappadu`
   → *Add-ons → Secrets → Add a new secret* → label `GEMINI_API_KEY`. The Kaggle API
   cannot create secrets, and this pass never attempts to read them.
2. **Run All, then Save Version** so the public page shows real-inference output. Without
   the secret the notebook still runs, in clearly disclosed mock mode.

Verification after those steps: the saved output should show
`provider: google-genai`, `model: gemma-4-26b-a4b-it`, a `get_marine_conditions`
function call, and the marine disclaimer — with no key value anywhere in the output.
