# Verified Facts Register

Access date for all entries: 2026-07-29.

| # | Claim | Source(s) | Supporting passage / evidence | Intended use | Confidence | Human verification required? |
|---|---|---|---|---|---|---|
| F1 | *Octopus cyanea* Gray, 1849 is an accepted species (GBIF key 2289535; iNat taxon 49056 "Day Octopus", active) | S3, S4 | GBIF match `status: ACCEPTED`; iNat `is_active: true` | Species catalogue | High | No |
| F2 | Mauritius enacted octopus-fishing closure regulations in 2016 with a 15 August–15 October closure | S1, S9 | FAOLEX-hosted regulation PDF titled "Fisheries and Marine Resources (Fishing of Octopus) Regulations 2016"; 2016 ministerial announcement of 15 Aug–15 Oct closure | Basis of seasonal rule record | High (that it existed in 2016) | — |
| F3 | **No confirmation found that a 15 Aug–15 Oct 2026 closure is currently in force**; instruments under the 2007 Act may have been superseded by later legislation | Searches of S1/S2 + web, 2026-07-29 | Ministry index page contains no closure notice; no 2026 notice located | Rule is stored as `provisional`; app must show "Verify against the latest official fisheries notice" | — | **YES — blocking for any 'verified' label** |
| F4 | No official minimum-size values were verified for the four P0 fish species during the sprint | Attempted S1/S2 | No primary text retrieved | Minimum-size rules stored as `unavailable`; engine returns `unknown` | — | YES |
| F5 | Open-Meteo Marine API returns wave/swell height, direction, period (and SST where available) for Mauritius coordinates without an API key | S5 + live call 200 (`marine-api.open-meteo.com`, lat -20.16 lon 57.5) | Live JSON response received at baseline | Marine service | High | No |
| F6 | A 15 January–15 March closure period appears in the historical Mauritius octopus-closure programme narrative, but no current legal instrument confirming it was located | S10 + searches | Programme description of temporary closures | Stored as `historical_note` only; NOT used in rule evaluation | Low | YES |

Nothing in this register may be presented in the app or writeup at a stronger confidence than stated here.
