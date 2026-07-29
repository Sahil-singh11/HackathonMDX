# Fisheries Rules Register

Deterministic rules only. Every rule carries source, dates, and verification status. Missing/ambiguous ⇒ engine returns `unknown`.

## R-OCT-CLOSE-2016 — Octopus seasonal closure
- Species: Octopus cyanea (and octopus generally under the regulation)
- Rule: no fishing 15 August – 15 October (annual pattern per the 2016 regulations)
- Source: S1 — Fisheries and Marine Resources (Fishing of Octopus) Regulations 2016, https://faolex.fao.org/docs/pdf/mat161116.pdf
- Effective date (original): 2016-08-15 · Verification date: 2026-07-29
- **Verification status: `provisional`** — current-year (2026) applicability NOT confirmed; possible supersession by post-2016 legislation (see VERIFIED_FACTS F3). The engine evaluates the window deterministically but always attaches: "Rule recorded from the 2016 regulations; current-year confirmation pending. Verify against the latest official fisheries notice."
- Boundary tests: 14 Aug (out), 15 Aug (in), 15 Oct (in), 16 Oct (out), real date 29 July (out — must NOT show closure active).

## R-OCT-CLOSE-JAN — Historical January–March closure
- 15 January – 15 March appears in historical closure-programme narrative only (F6). **Status: `historical_note` — NOT evaluated by the engine.**

## R-MINSIZE-* — Minimum sizes (all four P0 fish species)
- **Status: `unavailable`** — no primary legal text verified during the sprint (F4). Engine returns `unknown` + "Verify against the latest official fisheries notice." No values are invented.

## Versioning
Rules live in `data/rules/species_rules.json` with `rules_version`, per-rule `source_id` into `data/rules/source_register.json`. Any change bumps `rules_version` and adds a decision-log entry.
