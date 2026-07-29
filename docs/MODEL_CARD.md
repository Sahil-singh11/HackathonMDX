# Model Card — Lamer Konekte analysis stack

## Production model
- **gemma-4-26b-a4b-it** (hosted, Gemini API, official `google-genai` SDK). Roles: image understanding, constrained species suggestion, Morisyen/English intent, structured output, native function calling. Bounded by system instruction + server-side guards (candidate allow-list, schema ladder, coordinate redaction).
- Status: code-complete; live gates BLOCKED pending API key (`docs/GEMMA_GATES.md`). Until then the app uses the disclosed deterministic mock.

## Fine-tuned adapter
- None integrated. Training prepared but not launched (see `docs/MODEL_TRAINING_REPORT.md`). No adapter claims are made.

## Out-of-scope uses (enforced, not just documented)
Legal decisions · size verification · authoritative species ID · navigation-safety advice · real government submission.

## Evaluation
Prototype benchmark harness with 32 Morisyen/English cases + image-quality + rule-boundary + function-calling groups. Current numbers are mock-pipeline metrics (`docs/BASELINE_REPORT.md`); hosted metrics land in the same files once the key exists.

## Ethical considerations
Fisher confirmation is mandatory; unknown-over-invented for regulations; provisional Morisyen names marked; privacy floor (in-memory images, rounded coordinates). See `docs/RESPONSIBLE_AI.md`, `docs/LIMITATIONS.md`.
