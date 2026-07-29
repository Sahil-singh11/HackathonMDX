# Risk Register — Lamer Konekte

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| 1 | `GEMINI_API_KEY` never provided | Medium | Gemma gates + hosted demo blocked (30-pt rubric area at risk) | Hosted provider code-complete + gate script ready; disclosed mock keeps demo functional; escalated as top human action | **OPEN — blocking** |
| 2 | Kaggle auth never provided | Medium | Training cannot launch | Notebooks + data + push scripts ready; honest blocker report satisfies "attempted and documented" | OPEN |
| 3 | WSL RAM (7.4 GB) too small for local Gemma | High | Edge bonus unreachable | Morisyen bonus is the primary 10-pt path; edge stays P3, never claimed | Accepted |
| 4 | Fisheries rule accuracy (octopus closure dates) | Medium | Legal-misinformation risk | Rules carry sources + verification status; unverified ⇒ `unknown`; UI always says "verify official notice"; boundary-date tests | Mitigated in design |
| 5 | Hosted API latency/outage during jury demo | Medium | Demo stalls | Visible hosted→mock fallback; cached hero cases; failure-recovery script | Mitigated |
| 6 | Repo made public with a secret | Low | Disqualification-level | `.gitignore` from minute one; history scanned clean; release gate re-scans | Mitigated |
| 7 | Time overrun on frontend polish | High | P0 flows unfinished | Cut list order (animation → map → extra species → audio → edge → big training) | Watch |
| 8 | Morisyen wording errors | Medium | Bonus credibility | Provisional-name statuses; human-review register; critical strings flagged | OPEN (needs native review) |
| 9 | Deadline assumption wrong | Medium | Freeze mis-timed | Assumption documented in TIMEBOX; team asked to confirm | OPEN |
| 10 | No deployment platform credential | Medium | No public URL | Kaggle notebook is the sanctioned secondary demo; fallback kit prepared | OPEN |
