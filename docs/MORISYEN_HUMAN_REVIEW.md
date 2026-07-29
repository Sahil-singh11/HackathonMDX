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
| 8 | `dashboard.*` (18 new keys) | "Byenveni ankor", "Lapes zordi", "An atant", "Dernie sorti", "Foto → Idantifie → Anrezistre", "Verifie avan to sorti", "Pankor ena lapes", "kalite pwason anrezistre", "Prepar to deklarasion mansiel", "Pare kan to pare", "To premie lapes pou aparet isi. Tap \"Anrezistre enn lapes\" pou koumanse.", "Anrezistre to premie lapes", "Get tou", "vag", "Aktivite resan", "Aster mem", "Zordi", "Yer" | New bento dashboard redesign (2026-07-29) — none previously reviewed | _pending_ | | |
| 9 | `catch.tip.*`, `catch.tag.*`, `catch.progress.*`, `catch.identifying`, `catch.recordAnother`, `catch.viewLog`, `catch.location`, `catch.regulatoryStatus`, `catch.measuredSize`, `catch.pendingConfirmation`, `catch.recent`, `catch.voiceInput` (21 new keys) | "Bon lalimier", "Tou pwason vizib", "Met regleman", "Evit figir", "Resif", "Lamer fon", "Gramatin", "Tanto", "Pre kot", "Pe eskane foto", "Pe idantifie lespes", "Pe verifie regleman", "Pe idantifie lespes…", "Anrezistre enn lot lapes", "Get zistwar lapes", "Landrwa", "Stati regleman", "Groser mezire", "An atant — konfirm ek mezir pou verifie", "Resan", "Antre par vwa" | New step-by-step Record-a-catch redesign (2026-07-29) — none previously reviewed | _pending_ | | |

Process: reviewer edits `frontend/src/i18n/mfe.json` (and catalogue names), records the correction here, upgrades name status in `research/SPECIES_NAME_REGISTER.md` to `human_verified`, and re-runs `npm run build`.
