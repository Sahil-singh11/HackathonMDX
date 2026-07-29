# Training Dataset Card

Built by `training/scripts/build_training_data.py` → `training/data/{train,validation,test}.jsonl`.

## Record types
1. **image_identification** — licensed manifest images; instruction to suggest ONLY from the candidate list with uncertainty; expected constrained JSON (species, confidence, characteristics, `confirm_species` next step). Split inherited from the image manifest (observation-level split → no image leakage).
2. **text_intent** — Morisyen/English instructions with expected intent and expected allow-listed function call. Paraphrase families are split as whole families (template de-dup: all paraphrases of one family land in one split).
3. **safety** — expected safe responses: refuse legality decisions, refuse invented rules, refuse navigation guarantees, resist prompt injection.

## Leakage controls
- Image splits follow `sha256(observation_id)` from the manifest (no augmented copy can cross splits because variants inherit the parent row's split).
- Text template families hashed as a unit.
- pytest: `backend/tests/test_dataset_leakage.py`.

## Intended use
Kaggle QLoRA (Mode A multimodal on E2B / Mode B text-structured) per `docs/TRAINING_PLAN.md`. Not a general-purpose dataset; targets are aligned with the app's safety contract (suggest-never-declare, unknown-over-invented).

## Honesty
Expected outputs are heuristic supervision written by the team, not gold biological annotation; species labels come from research-grade iNaturalist community IDs.
