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

/** Mirrors register_default_pillars() in backend/app/pillars/registry.py.
 *
 * Descriptions are copied from the registry VERBATIM, including the rewrite that
 * took the task references, file paths and version strings out of them. If the
 * two drift, the offline view starts claiming things the running app does not.
 *
 * `owner` is deliberately blank here. The field still exists on the API, but
 * nothing renders it any more (it was internal workstream attribution), and a
 * name left in a file on the render path is a name waiting to reappear.
 */
export const FIXTURE_PILLARS: PillarDescriptor[] = [
  {
    pillar_id: 'fisheries',
    pillar_name: 'Sustainable Fisheries & Aquaculture',
    status: 'live', enabled: true, implemented: true,
    owner: '',
    description:
      'Record a catch from a photo, check it against the GN 167/2016 size and '
      + 'season rules, log it to a tamper-evident record, and prepare a declaration.',
    sources: [
      { name: 'Open-Meteo Marine', url: 'https://marine-api.open-meteo.com/v1/marine',
        description: 'Sea state and forecast for Mauritian waters.', status: 'verified' },
      { name: 'Mauritius fisheries size and season rules', url: null,
        description: 'Held on the device; works with no signal.', status: 'verified' },
    ],
    endpoints: [],
  },
  {
    pillar_id: 'transport',
    pillar_name: 'Marine Transport & Trade',
    status: 'registered', enabled: false, implemented: true,
    owner: '',
    description:
      'Live sea state on the Port Louis approach, sorted into good, moderate and '
      + 'poor transit windows against fixed limits. Vessel tracking is not '
      + 'included: no public receiver covers Mauritius.',
    sources: [{ name: 'Open-Meteo Marine', url: 'https://marine-api.open-meteo.com/v1/marine',
        description: 'Sea state and forecast for Mauritian waters.', status: 'verified' }],
    endpoints: [],
  },
  {
    pillar_id: 'tourism',
    pillar_name: 'Sustainable Ocean Tourism',
    status: 'registered', enabled: false, implemented: true,
    owner: '',
    description:
      'Beach and lagoon conditions for tour operators: swimming, snorkelling and '
      + 'small-boat suitability, site by site.',
    sources: [{ name: 'Open-Meteo Marine', url: 'https://marine-api.open-meteo.com/v1/marine',
        description: 'Sea state and forecast for Mauritian waters.', status: 'verified' }],
    endpoints: [],
  },
  {
    pillar_id: 'energy',
    pillar_name: 'Ocean-Based Renewable Energy',
    status: 'registered', enabled: false, implemented: true,
    owner: '',
    description:
      'Wind and wave resource at candidate offshore sites, for judging where '
      + 'marine energy is worth studying.',
    sources: [{ name: 'Open-Meteo Marine', url: 'https://marine-api.open-meteo.com/v1/marine',
        description: 'Sea state and forecast for Mauritian waters.', status: 'verified' }],
    endpoints: [],
  },
  {
    pillar_id: 'finance',
    pillar_name: 'Blue Finance',
    status: 'registered', enabled: false, implemented: true,
    owner: '',
    description:
      'Checks a blue-bond or ESG document against blue-finance criteria. Findings '
      + 'are advisory, and nothing is changed or filed.',
    sources: [{ name: 'Uploaded documents', url: null,
      description: 'Only the document you upload. Nothing is fetched from outside.', status: 'none' }],
    endpoints: [],
  },
  {
    pillar_id: 'biotech',
    pillar_name: 'Marine Biotechnology',
    status: 'registered', enabled: false, implemented: false,
    owner: '',
    description: 'Cataloguing assistance for marine research literature and samples.',
    sources: [{ name: 'Uploaded documents', url: null,
      description: 'Only the document you upload. Nothing is fetched from outside.', status: 'none' }],
    endpoints: [],
  },
]

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
