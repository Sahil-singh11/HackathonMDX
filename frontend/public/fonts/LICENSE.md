# Bundled fonts — licences and provenance

All three families are licensed under the **SIL Open Font Licence 1.1 (OFL-1.1)**,
which explicitly permits bundling, self-hosting and redistribution with an
application, including commercially, provided the fonts are not sold on their own
and this notice is retained.

These files are **self-hosted deliberately**: Lamer Konekte is an offline-first app
for fishers who routinely have no signal, so a Google Fonts CDN request would fail in
exactly the situation the app exists to serve. Each file is the **latin subset only**,
to keep the offline bundle small.

| File | Family | Copyright | Upstream |
|---|---|---|---|
| `bricolage-grotesque-var-latin.woff2` | Bricolage Grotesque (variable, 400–800) | Copyright © 2022 The Bricolage Project Authors | https://github.com/ateliertriay/bricolage |
| `public-sans-var-latin.woff2` | Public Sans (variable, 100–900) | Copyright © 2015-2018 Public Sans Project Authors; based on Libre Franklin | https://github.com/uswds/public-sans |
| `ibm-plex-mono-400-latin.woff2` | IBM Plex Mono 400 | Copyright © 2017 IBM Corp. | https://github.com/IBM/plex |
| `ibm-plex-mono-500-latin.woff2` | IBM Plex Mono 500 | Copyright © 2017 IBM Corp. | https://github.com/IBM/plex |
| `ibm-plex-mono-600-latin.woff2` | IBM Plex Mono 600 | Copyright © 2017 IBM Corp. | https://github.com/IBM/plex |

Retrieved 2026-07-29 via the Google Fonts CSS2 API, which serves the upstream OFL
binaries unmodified. Full OFL-1.1 text: https://openfontlicense.org

**Fallbacks.** `styles/tokens.css` declares `ui-sans-serif`/`system-ui` and
`ui-monospace` fallbacks on every font role, so if a file fails to load the app stays
fully legible — it only loses the typographic personality.
