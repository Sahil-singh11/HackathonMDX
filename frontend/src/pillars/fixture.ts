/* Workstream 2 — local fixture for the pillar shell.
 *
 * Two jobs:
 *
 * 1. Let /pillars render with the backend down. The six descriptors mirror
 *    backend/app/pillars/registry.py exactly (government naming verbatim), so
 *    the offline view is the truth as of this build rather than an invention.
 *
 * 2. Exercise all four data_kind states in the ProvenanceBadge. Only `fisheries`
 *    is implemented today, so no live pillar can produce a `sample` or
 *    `synthetic` result yet — the badge demo has to come from somewhere, and a
 *    labelled fixture is the honest place. These four are NEVER shown as pillar
 *    output; they appear only in the badge reference on the index page, under a
 *    heading that says they are examples.
 */
import type { DataProvenance, PillarDescriptor } from './types'

/** Mirrors register_default_pillars() in backend/app/pillars/registry.py. */
export const FIXTURE_PILLARS: PillarDescriptor[] = [
  {
    pillar_id: 'fisheries',
    pillar_name: 'Sustainable Fisheries & Aquaculture',
    status: 'live', enabled: true, implemented: true,
    owner: 'team (shipped)',
    description:
      'Production pillar: multimodal catch analysis, GN 167/2016 rule checks, '
      + 'append-only traceability ledger, declarations.',
    sources: [
      { name: 'Open-Meteo Marine', url: 'https://marine-api.open-meteo.com/v1/marine',
        description: 'Marine conditions with startup pre-warm and cache.', status: 'verified' },
      { name: 'Species rules catalogue', url: null,
        description: 'data/rules/species_rules.json (v1.1.0) — local, versioned.', status: 'verified' },
    ],
    endpoints: ['/api/analyse-catch', '/api/catches', '/api/ledger', '/api/verify/{id}', '/api/declarations'],
  },
  {
    pillar_id: 'transport',
    pillar_name: 'Marine Transport & Trade',
    status: 'registered', enabled: false, implemented: false,
    owner: 'Yadhav (WS1)',
    description: 'Port Louis arrivals brief from live AIS positions; counts and ETAs stay deterministic.',
    sources: [{ name: 'aisstream.io', url: 'https://aisstream.io',
      description: 'Real-time AIS WebSocket. Candidate until a live Port Louis message is captured.',
      status: 'candidate' }],
    endpoints: [],
  },
  {
    pillar_id: 'tourism',
    pillar_name: 'Sustainable Ocean Tourism',
    status: 'registered', enabled: false, implemented: false,
    owner: 'Dhanesh (WS2)',
    description: 'Lagoon/beach condition briefs for eco-tourism operators on the existing marine data spine.',
    sources: [{ name: 'Open-Meteo Marine', url: 'https://marine-api.open-meteo.com/v1/marine',
      description: 'Already integrated and cached by the app.', status: 'verified' }],
    endpoints: [],
  },
  {
    pillar_id: 'energy',
    pillar_name: 'Ocean-Based Renewable Energy',
    status: 'registered', enabled: false, implemented: false,
    owner: 'Dhanesh (WS2)',
    description: 'Wind/wave resource summaries for offshore-energy siting from marine forecast data.',
    sources: [{ name: 'Open-Meteo Marine', url: 'https://marine-api.open-meteo.com/v1/marine',
      description: 'Already integrated and cached by the app.', status: 'verified' }],
    endpoints: [],
  },
  {
    pillar_id: 'finance',
    pillar_name: 'Blue Finance',
    status: 'registered', enabled: false, implemented: false,
    owner: 'Shirish (WS3)',
    description: 'Blue-bond / ESG document checks against blue-finance criteria; findings advisory, read-only.',
    sources: [{ name: 'Uploaded documents', url: null,
      description: 'User-supplied documents; no external feed.', status: 'none' }],
    endpoints: [],
  },
  {
    pillar_id: 'biotech',
    pillar_name: 'Marine Biotechnology',
    status: 'registered', enabled: false, implemented: false,
    owner: 'Shirish (WS3, stretch)',
    description: 'Literature/sample cataloguing assistance for marine research (stretch).',
    sources: [{ name: 'Uploaded documents', url: null,
      description: 'User-supplied documents; no external feed.', status: 'none' }],
    endpoints: [],
  },
]

export const FIXTURE_NOTE =
  'Pillar results always carry a DataProvenance block: source, retrieval time, '
  + 'data_kind (live|cached|sample|synthetic), inference provider, and what the '
  + 'data does not cover.'

function isoMinutesAgo(mins: number): string {
  return new Date(Date.now() - mins * 60000).toISOString()
}

/**
 * One example per data_kind, for the badge reference on the index page.
 * Labelled as examples wherever rendered — never presented as pillar output.
 */
export const BADGE_EXAMPLES: DataProvenance[] = [
  {
    source_name: 'Open-Meteo Marine',
    source_url: 'https://marine-api.open-meteo.com/v1/marine',
    retrieved_at: isoMinutesAgo(0),
    data_kind: 'live',
    model_provider: 'gemma_hosted',
    coverage_note:
      'Forecast model output for a rounded coordinate, not a measurement at your exact position. '
      + 'Informational only — never a safety or navigation decision.',
  },
  {
    source_name: 'Open-Meteo Marine',
    source_url: 'https://marine-api.open-meteo.com/v1/marine',
    retrieved_at: isoMinutesAgo(25),
    data_kind: 'cached',
    model_provider: 'gemma_hosted',
    coverage_note:
      'Served from an earlier fetch, so conditions may have changed since. '
      + 'Does not cover crowding, water quality or local hazards.',
  },
  {
    source_name: 'Committed capture (data/samples)',
    source_url: null,
    retrieved_at: isoMinutesAgo(60 * 26),
    data_kind: 'sample',
    model_provider: 'mock',
    coverage_note:
      'A stored capture kept so the surface works without a live feed. It reflects one past '
      + 'moment and is not current for any site.',
  },
  {
    source_name: 'Generated fixture',
    source_url: null,
    retrieved_at: isoMinutesAgo(2),
    data_kind: 'synthetic',
    model_provider: 'mock',
    coverage_note:
      'Generated values used to exercise the interface. These are not observations of anything '
      + 'and must never be read as real conditions or a real assessment.',
  },
]
