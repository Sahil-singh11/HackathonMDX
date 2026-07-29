# AI Limitations — stated plainly

These are the limits of the AI in this submission. They are enforced in code where
possible and disclosed in the product where not.

---

## What the AI must never do (enforced server-side, tested)

- **No authoritative species identification.** The model suggests, constrained to a
  candidate shortlist; the fisher must confirm. Names without an allow-listed id are
  stripped.
- **No legality decisions.** Only the deterministic rules engine decides, and only after
  species confirmation with a measured length.
- **No visual measurement as verified measurement.** A size judged from a photo is
  labelled unverified and never used for legal reasoning.
- **No marine-safety guarantees.** Conditions are informational; every response points to
  official advisories.
- **No invented fisheries rules.** Zero accepted legal hallucinations across all
  evaluated sets — and the application would reject one anyway.
- **No real ministry submission.** The declaration endpoint is a mock demonstration and
  is labelled as such everywhere.
- **No un-validated tool execution.** 12 allow-listed functions, explicit map, Pydantic
  argument validation; unknown names are rejected and traced.

## Model and evaluation limits

- **The fine-tuned E2B adapter is NOT production.** It failed the pre-registered
  acceptance gates (tool accuracy 58.8% vs 70%; external intent 78.1% vs 80%) and ships
  disabled. Hosted `gemma-4-26b-a4b-it` is the only production model.
- **85.3% is not universal accuracy.** It is intent accuracy on one 34-record internal
  test where a single record is worth 2.9 pp. External: 78.1% (32 records). Challenge set
  (unseen families): 70.8%. Numbers this small carry wide error bars and are reported
  separately, never blended.
- **Tool selection is the known weak point** (58.8%, unchanged v1→v2). A router that
  picks the right intent but the wrong function still executes the wrong thing — which is
  exactly why the gate rejected the adapter.
- **The internal declaration recall of 1.000 partly reflects stylistic proximity** to the
  training families; on never-seen challenge families it is 0.727.
- **Hosted latency is ~10 s median end-to-end** (structured stage ~4–6 s). Managed by
  routing, caching and progress UX — fine-tuning does not change hosted API latency.
- **Hosted availability is not under our control.** Under load the API returns 503; the
  app falls back to a deterministic mock with a visible disclosure, never silently.

## Data limits

- **308 of 338 training records are AI-generated, unreviewed Morisyen.** The 30 reviewed
  records were approved as written by the project owner, who is **not a verified
  native/fluent speaker**. No part of this dataset may be described as
  native-speaker verified.
- **All user inputs are synthetic.** No real fisher messages were collected; no consent
  flow exists for that yet.
- **Intent distribution is deliberately unbalanced** (declaration-heavy) to attack a
  measured failure — it does not reflect real traffic.
- The species catalogue covers **5 species**; suggestions outside it return unknown.
- Species image labels derive from research-grade iNaturalist community IDs, not expert
  taxonomic annotation.

## Product limits

- Morisyen safety strings in the UI await native-speaker sign-off
  (`docs/MORISYEN_HUMAN_REVIEW.md`).
- Offline mode queues actions; it does not run the hosted model.
- The public demo runs on a free tier that sleeps when idle (first load 30–60 s).
