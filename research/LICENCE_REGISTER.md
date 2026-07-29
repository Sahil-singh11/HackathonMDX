# Licence Register

| Asset class | Source | Licence | Redistribution | Notes |
|---|---|---|---|---|
| Marine forecast data | Open-Meteo | CC-BY 4.0 | Yes with attribution | Attribution string shown in UI: "Weather data by Open-Meteo.com" |
| Taxonomy records | GBIF / iNaturalist APIs | CC0/CC-BY per record | Metadata yes | Media licences tracked per-file in `data/manifests/species_images.csv` |
| iNaturalist photos | per-photo licence field | Only CC0/CC-BY/CC-BY-NC accepted by the download script | CC0/CC-BY yes with credit; CC-BY-NC **evaluation-only, not redistributed** | Script rejects all-rights-reserved media |
| Synthetic test images | generated in-repo | Project licence (MIT) | Yes | Blur/exposure/invalid variants |
| Team photos | team members | Written consent recorded in manifest | Only with consent flag | None collected yet |
| Gemma model outputs | Google Gemma Terms of Use | Per Gemma terms | — | Hosted use via Gemini API |
| Code | this repository | MIT (LICENSE) | Yes | |
| Logo/icon | generated in-repo (original SVG) | MIT | Yes | Safe to redistribute |

Gate: `scripts/release_gate.sh` fails if any manifest row has `redistribution_permission != yes` for a file tracked by git.
