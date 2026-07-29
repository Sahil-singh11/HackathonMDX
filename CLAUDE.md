# Lamer Konekte — frontend working agreement

Offline-first catch-to-certificate app for Mauritian artisanal fishers, plus a
shore-side review surface for ministry officers.

Read this before writing any code. It is the contract that lets three people
build one frontend at the same time without colliding.

---

## FILE OWNERSHIP

**Sahil:** `styles/`, `theme/`, `components/{shell,ocean,a11y,ui}`,
`pages/{Dashboard,Marine,DemoControls,Privacy,About}`, router (`App.tsx`), `lib/`.

**Dhanesh:** `pages/{CatchFlow,History,Queue}`, `components/{capture,log}`.

**Shirish:** `pages/{Declaration,stubs}` → `components/{declaration,authority,verify}`.

**FROZEN:** `styles/tokens.css` and `components/ui/*` are read-only for everyone,
including Sahil. Need a variant? Wrap the primitive inside your own lane folder.
Never edit it.

**Never create or modify a file outside your lane.**

Lane notes for pages that predate the new IA:
- **Queue → Dhanesh.** It is the other half of the capture flow.
- **Proof → Shirish.** Check it against `/verify/:id` **before building anything
  new** — both surface "prove this record is what it claims", and two competing
  answers to that would be worse than either alone.
- **DemoControls, Privacy, About → Sahil.** Frozen; leave them as they are.

---

## Stack

React 18 · TypeScript (strict, `noUnusedLocals`) · Vite 5 · react-router-dom 6 ·
Zustand · TanStack Query · lucide-react. Served in production by FastAPI from
`frontend/dist`.

```bash
cd frontend && npm run dev     # Vite on :5173, proxies /api and /health to :8000
cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000
cd frontend && npm run build   # MUST pass before you push
cd backend && .venv/Scripts/python -m pytest tests -q
```

---

## Two palettes, and why

This app already shipped working pages before the design system existed. There
are now **two token sets, deliberately not merged**:

| | Where | Used by |
|---|---|---|
| Legacy | `styles.css` (`--primary-navy`, `--accent-teal`, `--surface-card`…) | Pages that already shipped |
| Semantic | `styles/tokens.css` (`--bg`, `--surface`, `--text`, `--accent`…) | **All new code** |

They are not aliased to each other because the palettes are genuinely different
colours — `--accent-teal #1b9aaa` vs `--lagoon #0E7C86` is a ΔE of about 12, a
clearly visible shift. Aliasing them would have silently restyled every page
that already worked.

**New code consumes semantic names only.** Never a raw palette value
(`--lagoon`), never a legacy token (`--accent-teal`), never a hex literal.

Load order is load-bearing and must not be reordered:

```
styles/tokens.css  ->  styles/base.css  ->  styles.css
```

`styles.css` loads last so its existing rules win any collision. That ordering
is the entire no-visual-regression guarantee.

Anything you build should be wrapped in `.lk-scope`, which opts it into the new
typography and semantic colours. Existing pages are not wrapped, so they are
untouched.

---

## Tokens you may use

**Colour (semantic):** `--bg` `--bg-alt` `--surface` `--surface-raised`
`--surface-sunken` `--text` `--text-muted` `--text-invert` `--border`
`--border-strong` `--accent` `--accent-hover` `--accent-contrast`
`--accent-quiet` `--action` `--action-hover` `--action-contrast`
`--success` `--warning` `--danger` (+ `--*-quiet` variants)

- `--border` is decorative. **`--border-strong` is for real control edges**
  (inputs, checkboxes) and is the one tuned to pass 3:1 non-text contrast.
- `--action` is coral and is the *sparing* primary action. Its label text is
  **dark** (`--action-contrast`), because white on coral measures 2.81:1 and
  fails. The brand hex is unchanged; only the text on top of it is.

**Type:** `--font-display` (Bricolage Grotesque — page titles and big numbers
only) · `--font-body` (Public Sans — all UI text) · `--font-data` (IBM Plex Mono
— coordinates, timestamps, catch IDs, ledger hashes, weights, certificate refs;
**anything an officer would read aloud is mono**).
Sizes `--fs-xs|sm|base|md|lg|xl|2xl` = 12/14/16/20/28/40/56. **Body never below 16px.**

**Space:** `--sp-1..8` = 4/8/12/16/24/32/48/64. (`--space-1..9` is the legacy
ramp in `styles.css` — do not use it in new code.)

**Shape:** `--r-input` 4 · `--r-card` 12 · `--r-chip` 999 · `--touch-min` 56px.

**Motion:** `--motion-fast|base|slow`, `--ease-out`. All three become `0ms` under
`prefers-reduced-motion` or the a11y panel, so route every duration through them.

Fonts are **self-hosted** in `public/fonts/` (latin subset, OFL-1.1). Never add a
CDN font link: this app must work with no signal, which is exactly when a CDN
fetch fails.

---

## Themes

Three, switchable from the header or the a11y panel, persisted to localStorage,
seeded from system preference:

- **Day** — light, foam/sand surfaces.
- **Night** — dark. Folds the pre-existing `[data-theme='dark']` prep, so both
  attribute values work. Has an opt-in **night vision** mode that shifts to deep
  red so a fisher's dark adaptation survives a night crossing.
- **Sunlight** — extreme contrast for direct equatorial sun on a deck: pure
  white, near-black text, hard borders, no shadows, **ambient animation off**,
  64px touch targets. A real ship-deck problem, not a filter.

Applied as `data-theme` / `data-night-vision` / `data-text-scale` /
`data-reduce-motion` on `<html>`, so legacy pages get themed too.

All 32 contrast pairs across the four theme states meet the floor. If you add a
colour pair, check it.

---

## Component inventory (`components/ui`, frozen)

Import from the barrel: `import { Button, Card, FormField, Input } from '../ui'`

| Component | Key props |
|---|---|
| `Button` | `variant` primary/secondary/ghost/danger · `block` · `loading` · `icon` · `as='a'` |
| `Card` | `title` · `action` · `raised` · `flush` · `as` |
| `StatTile` | `label` · `value` · `hint` · `emphasis` · `icon` |
| `Badge` | `tone` neutral/accent/success/warning/danger · `icon` |
| `Divider` | `tight` |
| `FormField` | `label` · `hint` · `error` · `required` — render-prop wires id/describedby/invalid |
| `Input` / `Textarea` / `Select` / `DateField` | native attrs · `data` (mono role) |
| `Chip` | `selected` · `onToggle` · `icon` · `disabled` |
| `Checkbox` / `Radio` | `label` · `hint` + native attrs |
| `Sheet` | `open` · `onClose` · `title` · `footer` — focus trap, Escape, focus return |
| `ToastProvider` / `useToast` | `show(message, tone?, ms?)` |
| `Tooltip` | `label` — enhancement only, unreachable on touch |
| `Skeleton` | `width` · `height` · `text` · `count` |
| `EmptyState` | `title` · `body` · `icon` · `action` |
| `Spinner` | `label` · `size` |
| `ProgressStages` | `stages` · `current` · `done` |
| `Table` | `columns` · `rows` · `rowKey` · `caption` · `onRowClick` · `empty` — sortable, cards under 768px |
| `Tabs` | `tabs` · `active` · `onChange` — arrow-key roving focus |
| `Pagination` | `page` · `pageCount` · `onChange` · `label` |

Shared helpers: `useOffline()` (`lib/offline`) for connectivity and the queue —
do not write your own; `useAnnounce()` (`lib/announce`) for the shared aria-live
region; `useToast()` for transient confirmations.

---

## Accessibility floor — non-negotiable

- Minimum touch target **56×56px** (gloves, wet hands, a moving boat).
- Visible focus ring on everything: 2px `--accent`, 2px offset.
- Full keyboard nav; skip-to-content is the first tab stop; logical tab order.
- One `h1` per page, correct heading order, semantic landmarks.
- Text scales to 125% and 150% without breaking layout — **test it**.
- Announce async outcomes via `useAnnounce()`. Outcomes, not progress spam.
- **No icon-only buttons.** Every icon has a label or `aria-label`.
- **Colour is never the only signal** — pair it with an icon or text.
- Contrast ≥4.5:1 body, ≥3:1 large text and UI borders, in **every** theme.

---

## Honesty rules — these are the point of the product

1. **Every AI suggestion is advisory.** Show a confidence *band* (low/moderate/
   high), never a fabricated percentage — the API returns a label, not a number.
   Always offer alternatives and a manual-entry path. Never present a suggestion
   as a verdict.
2. **Every mock government interaction is labelled MOCK**, including on the
   receipt. `/declaration` must never be mistakable for a real filing.
3. **`/verify/:id` must not overclaim.** It can prove a record is unaltered since
   it was logged. It cannot prove the underlying claim is true. Say so on the page.
4. **Never invent data you do not have.** The backend stores no photos (analysed
   in memory, never written to disk) and no GPS beyond a rounded area, and has
   **no ledger, certificate or officer tables at all**. `getSubmission`,
   `listSubmissions`, `verifyCertificate` and `verifyLedger` therefore reject
   rather than return fixtures. Build the UI against real endpoints or show an
   honest "not available yet" state — do not fake a green "verified".
5. **Offline is the expected state, not an error.** Never style it red.

---

## Shared files, and how not to fight over them

- **Router (`App.tsx`) — frozen.** All routes are registered. Need one? Ask Sahil.
- **`api/client.ts` — keep functions ALPHABETICAL.** Fill in only the bodies you
  own (ownership is listed in the file). Alphabetical order keeps three people's
  diffs from landing next to each other.
- **`package.json`** — announce before installing, push immediately after.

### Routes

| Path | Page | Owner |
|---|---|---|
| `/` | Home | Sahil |
| `/sea` | Sea conditions | Sahil |
| `/record` | Record a catch | Dhanesh |
| `/log` | Catch log | Dhanesh |
| `/queue` | Offline queue | Dhanesh |
| `/declaration` | Declaration | Shirish |
| `/authority` | Authority dashboard (stub) | Shirish |
| `/verify/:id` | Certificate verification (stub) | Shirish |
| `/proof` | Technical proof | Shirish |
| `/demo` `/privacy` `/about` | Frozen | Sahil |

`/marine`, `/catch` and `/history` redirect to `/sea`, `/record` and `/log` so
existing links, QR codes and demo scripts keep working.

Fisher routes render inside `FisherShell` (ambient ocean layer + tab bar).
`/authority` and `/verify/:id` render inside `PlainShell`: **no fisher chrome and
no ambient animation** — a working tool and a public proof page, not the on-boat
experience. They are also reachable **without onboarding**, because an officer or
a buyer scanning a QR code is not a fisher and must not be asked to pick a
fishing area first.

---

## Gotchas already paid for

- **Deep links used to 404.** `StaticFiles(html=True)` only serves `index.html`
  for `/`. A SPA fallback now exists in `backend/app/main.py`, covered by
  `tests/test_spa_fallback.py`. It deliberately still 404s missing assets and
  unmatched `/api/*` routes. When fixing it, note StaticFiles hands over
  **OS-native separators**, so a `startswith("api/")` check passes on Linux and
  silently fails on Windows.
- **Screenshot comparisons of Home are nondeterministic** unless you force
  reduced motion — the count-up animation and page transition land differently
  between runs and produce phantom diffs.
- **`font:` is a shorthand** that also sets `line-height`. An unscoped
  `button { font: inherit }` silently moved the header language pill. Keep
  element selectors scoped to `.lk-scope`.
- **`test_hosted_integration.py` hits the live Gemma API** and fails with 503
  when Google is busy. Those failures are not yours; the rest of the suite is
  deterministic.
