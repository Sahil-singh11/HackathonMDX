# AI Step 3 — Training Readiness

Branch: `ai-modeling` · Base commit: `b171304` · Assessed: 2026-07-29 15:19 MUT

No secret value is printed anywhere in this document. Credentials are reported as
present/absent only.

---

## 1. Verdict

**READY TO TRAIN.** No hard blocker. The one anticipated blocker (Hugging Face licence
acceptance for the base model) does not apply.

| Requirement | Status | Evidence |
|---|---|---|
| Git branch / clean tree | **OK** | `ai-modeling` @ `b171304`, working tree clean |
| Kaggle CLI | **OK** | Kaggle CLI 2.2.3 at `~/AppData/Roaming/Python/Python313/Scripts/kaggle` |
| Kaggle authentication | **OK** | `~/.kaggle/kaggle.json` present; `kaggle kernels list --mine` returned 6 kernels for `yuvineappadu` |
| Base model exists | **OK** | `google/gemma-4-E2B-it` — HF API returns the repo, 3 940 335 downloads |
| Base model access | **OK — ungated** | HF API reports `gated: false`; `config.json` and `tokenizer_config.json` fetched anonymously |
| `HF_TOKEN` | **ABSENT — not required** | Not in `.env`, not in the process environment, no `~/.cache/huggingface/token`. Not needed because the model is ungated |
| Official chat template | **OK** | `chat_template.jinja` published 2026-07-09, with tool-calling support |
| Local GPU | **NONE** | `nvidia-smi` not available — training cannot run locally, as anticipated |
| Kaggle GPU | **Assumed available, unverified** | Kaggle exposes no quota API; verified at notebook run time |
| Existing dataset | **Not reusable for this objective** | 72 records, image-identification schema |
| External benchmark | **OK** | 32 Morisyen cases, to be frozen as immutable |
| Time remaining | ~19.3 h to freeze, ~22.3 h to deadline | `docs/TIMEBOX.md` |

---

## 2. Credentials (presence only)

| Credential | `.env` | Process env | Other | Needed |
|---|---|---|---|---|
| `GEMINI_API_KEY` | present | absent | — | Steps 1–2 only |
| `HF_TOKEN` / `HUGGINGFACE_TOKEN` | absent | absent | no token cache | **No** — model ungated |
| `KAGGLE_USERNAME` / `KAGGLE_KEY` | absent | absent | `~/.kaggle/kaggle.json` **present** | Yes — satisfied via the JSON file |

`.env` is git-ignored (`.gitignore:2`). `kaggle.json` lives outside the repo and is also
ignored by name. Neither is read into any artifact.

---

## 3. Base model facts (verified, not assumed)

```
repo            google/gemma-4-E2B-it
gated           false          <- no licence acceptance step required
model_type      gemma4
architectures   ["Gemma4ForConditionalGeneration"]
files           config.json, generation_config.json, model.safetensors,
                processor_config.json, tokenizer.json, tokenizer_config.json,
                chat_template.jinja
```

Two details that change the notebook:

1. **The chat template is NOT in `tokenizer_config.json`** — it is a separate
   `chat_template.jinja`. `tokenizer_config.json` has no `chat_template` key, so code that
   reads the template from the tokenizer config alone would silently get `None`. Use
   `AutoProcessor` / `AutoTokenizer`, which load the `.jinja` file, and assert the template
   is non-empty before formatting anything.
2. **It is a conditional-generation (multimodal) checkpoint** with an audio feature
   extractor in `processor_config.json`. Load with `AutoProcessor` and address the language
   model for text-only LoRA.

No substitution is permitted: not Gemma 3, not Gemma 3n (`google/gemma-3n-E2B-it` exists
but is `gated: manual` and is a **different model**), not Gemini, not a community
conversion, not a different parameter size.

---

## 4. Dataset status

The existing `training/data/*.jsonl` (53 train / 11 validation / 8 test = **72 records**)
targets a *different* objective: image identification, with fields `image_path`,
`candidate_species`, `expected_json`. It has no `semantic_family`, no `provenance`, no
`human_review_status`, and no compact-prompt routing records.

**It is not reusable for the Step-3 objective and will not be silently repurposed.** A new
dataset (`Lamer Konekte AI Instructions v1`, ~240 records) is built alongside it. The 72
existing records remain as `existing_project_record` source material where a genuine
routing example can be derived.

The 32-case Morisyen benchmark (`evaluation/cases/morisyen_cases.json`) becomes
**immutable external test data**: checksummed, never trained on, never paraphrased.

---

## 5. Accelerator

- **Local:** none. `nvidia-smi` is absent; there is no usable local CUDA device. Full
  training will not be attempted locally under any circumstances.
- **Kaggle:** the notebook detects the device at run time (`torch.cuda.get_device_name`,
  total VRAM, BF16 capability) and derives its configuration from that rather than
  hardcoding for a specific accelerator. Kaggle publishes no quota API, so remaining GPU
  hours are confirmed from the session banner at run time and recorded in the report.

---

## 6. Residual risks

| Risk | Handling |
|---|---|
| Kaggle GPU quota exhausted this week | Notebook still validates and runs the untuned baseline on CPU-feasible subsets; training deferred; reported honestly |
| Kaggle image lacks a `transformers` new enough for `gemma4` | Notebook pins and prints versions, and fails loudly rather than falling back to another architecture |
| `Gemma4ForConditionalGeneration` LoRA target modules differ from Gemma 2/3 | Target modules are discovered by inspecting the loaded model, not hardcoded |
| OOM | Memory smoke test before full training; documented escalation ladder |
| Time overrun | Timebox with hard stop — see `docs/AI_STEP3_TIMEBOX.md` |
| AI-generated Morisyen quality | Marked `AI_generated_review_required`; human review queue; metrics split reviewed vs unreviewed |
