# Limitations — honest list

1. **Hosted latency**: all ten Gemma gates pass on real inference, but median latency is ≈16–25 s per call on the current key tier. The demo script accounts for this (progress states, pre-warmed hero cases); a paid tier or lighter model variant would improve it. Thinking-budget configuration is not supported for `gemma-4-26b-a4b-it` (recorded as WARN in the gates).
2. **Training not launched**: Kaggle CLI unauthenticated; data + notebooks + scripts are push-button ready; no adapter results are claimed.
3. **No edge inference**: no local Gemma has run (WSL RAM limits + missing HF licence acceptance); the edge bonus is not claimed.
4. **No audio**: the audio gate has no consented recordings; typed Morisyen is the input path; the API endpoint says so honestly.
5. **Rule verification**: the octopus closure is sourced to the 2016 regulations but its 2026 status is unconfirmed (`provisional`); no minimum sizes were verifiable, so those checks return `unknown`. The app never presents these as verified law.
6. **Morisyen review pending**: species names and critical strings await native-speaker sign-off (`docs/MORISYEN_HUMAN_REVIEW.md`).
7. **Mock-pipeline metrics only**: evaluation numbers measure the deterministic pipeline, not Gemma quality, and are labelled as such.
8. **Small dataset**: 60 licensed photos, mostly in-situ; not representative of deck/market conditions.
9. **Demo persistence**: SQLite on ephemeral storage; fine for a demo, not production.
10. **Mock ministry**: the declaration endpoint is a demonstration; no government integration exists.
