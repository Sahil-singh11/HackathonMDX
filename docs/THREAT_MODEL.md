# Threat Model (STRIDE-lite)

| Threat | Vector | Mitigation |
|---|---|---|
| Key exfiltration | Frontend bundle, logs, repo | Server-side only; redaction filter; dist grep in release gate; history scan |
| Prompt injection | Fisher note / image text | Untrusted-context instruction, allow-listed tools, deterministic rules outside the model, injection tests |
| Malicious upload | Zip bombs, polyglots, oversize | MIME allow-list, size cap, Pillow verify, in-memory handling, no file persistence |
| Legal misinformation | Model invents rules/sizes | Rules engine is deterministic + source-attributed; unknown-over-invented; UI verify-notice |
| Fake authority | Mock ministry mistaken as real | MOCK label on endpoint, UI, PDF and receipt; test-enforced |
| Unsafe navigation advice | "Is it safe to sail?" | No safety verdict path exists; disclaimer mandatory; eval cases assert no guarantee language |
| Data leakage | Precise coordinates, media in git | 2-dp rounding, gitignored raw media, manifest permission gate test |
| Availability | Hosted API outage during demo | Visible hosted→mock fallback, cached marine data, offline queue |
| DoS on demo | Upload flooding | Size caps; demo scope accepts residual risk (documented limitation) |
