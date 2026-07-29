# Judge Q&A Preparation

**Q: Is this real Gemma inference right now?**
A (if key inserted): "Yes — hosted `gemma-4-26b-a4b-it` via the official SDK; the badge shows model + latency, and gate results are in the repo." A (if not): "The hosted provider is code-complete and gated on a credential; what you see is a disclosed deterministic mock — we never present mock output as model inference. The Kaggle notebook runs the real model with a Kaggle Secret."

**Q: How do you stop the model hallucinating a species?** Constrained decoding by construction: the model only sees a retrieved shortlist, out-of-list answers are nulled server-side, and the fisher must confirm before anything downstream happens.

**Q: Could it say an illegal catch is legal?** No code path allows it. Legality comes only from a deterministic engine on a confirmed species + measured length; unverified rules return `unknown`; every result carries the official-verification notice.

**Q: Why is the octopus rule marked provisional?** We located the 2016 regulations as a primary source but could not confirm their 2026 status in-sprint — so the app says exactly that instead of pretending. That honesty *is* the compliance feature.

**Q: What about prompt injection?** Notes are untrusted context; tools are an explicit allow-list with Pydantic validation; we ship injection tests, and the trace page shows rejected calls.

**Q: Where does training stand?** Data, notebooks and push scripts are ready; the run was blocked on Kaggle credentials, and we report that rather than claim results. Acceptance criteria are strict — no improvement, no integration.

**Q: Edge/on-device?** Roadmap, not a claim: the local provider refuses to report "local" unless a real model loaded. Gemma E2B 4-bit is the candidate.

**Q: Why Morisyen first?** Adoption. A compliance tool nobody understands is a paperweight; a fisher-language assistant that happens to produce structured data is a policy instrument.

**Q: Business/sustainability?** The declaration schema is the asset: ministry consultation, cooperative deployments, and the marine-conditions surface as the daily-use hook.

**Q: Privacy of photos/locations?** Images analysed in memory and never stored; coordinates rounded to ~1 km; traces redacted; full reset button.
