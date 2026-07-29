# Morisyen Human Review Register

Native-speaker review is REQUIRED for the strings below before the demo. Team members (Morisyen speakers) sign off by filling the table.

| # | String (key) | Current wording | Critical because | Reviewer | Verdict / correction | Date |
|---|---|---|---|---|---|---|
| 1 | `marine.disclaimer` | "Previzion lamer zis pou lenformasion; kapav manke presizion pre ar lakot. Verifie avek bilten ofisiel avan sorti lor lamer." | Safety-critical marine wording | _pending_ | | |
| 2 | `limitation.permanent` | "Lamer Konekte donn dokimantasion lapes asiste par AI…" | Legal/AI disclosure | _pending_ | | |
| 3 | `decl.mockWarning` | "DEMONSTRASION (MOCK) — sa PA enn soumision ofisiel guvernman." | Mock-ministry disclosure | _pending_ | | |
| 4 | `catch.rule.verify` | "Verifie avek dernie lavi ofisiel lapes." | Rule-verification notice | _pending_ | | |
| 5 | `catch.estimatedSize` | "Groser AI estime (pa verifie — zame servi pou regleman)" | Unverified-size disclosure | _pending_ | | |
| 6 | Species names (5) | ourite / kapitenn / kordonye / vye / likorn | Provisional names must not mislead | _pending_ | | |
| 7 | `catch.queueOffline` | "To offline. Met sa lapes la dan lake pou sinkronize plitar?" | Offline consent wording | _pending_ | | |

Process: reviewer edits `frontend/src/i18n/mfe.json` (and catalogue names), records the correction here, upgrades name status in `research/SPECIES_NAME_REGISTER.md` to `human_verified`, and re-runs `npm run build`.
