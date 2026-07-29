/* Workstream 2 — bundled rules data.
 *
 * The three JSON files under data/ are imported AT BUILD TIME, so the rules
 * browser renders with zero connectivity on first visit — the acceptance
 * criterion for this page is "works with the backend down".
 *
 * One source of truth: these are the same files the backend rule engine reads
 * (backend/app/services/fisheries_rules/engine.py, .../species/retrieval.py).
 * Nothing is copied or rephrased. When the app is online, AssistantPage
 * revalidates against GET /api/rules/static and flags a version mismatch —
 * the bundle can lag the server by one deploy, and we say so rather than
 * pretending build-time data is live.
 */
import catalogueJson from '../../../data/processed/species_catalogue.json'
import sourcesJson from '../../../data/rules/source_register.json'
import rulesJson from '../../../data/rules/species_rules.json'

export interface SpeciesEntry {
  species_id: string
  scientific: string
  authority: string
  english: string
  morisyen: string
  morisyen_status: string
  habitat: string
  visible_characteristics: string[]
}

export interface RuleEntry {
  rule_id: string
  species_id: string
  rule_type: 'seasonal_closure' | 'minimum_size' | 'historical_note' | string
  minimum_length_cm?: number
  measurement?: string
  closed_from?: string
  closed_to?: string
  source_id: string
  source_title: string
  source_url: string
  citation?: string
  effective_date?: string
  verification_date?: string
  verification_status: string
  note?: string
  scope_note?: string
}

export interface SourceEntry {
  title: string
  publisher: string
  url: string
  publication_date: string | null
  access_date: string
  verification_status: string
  note: string
  citation?: string
}

export const RULES_VERSION: string = (rulesJson as { rules_version: string }).rules_version
export const RULES_DISCLAIMER: string = (rulesJson as { disclaimer: string }).disclaimer
export const CATALOGUE_NOTE: string = (catalogueJson as { note: string }).note

export const species: SpeciesEntry[] =
  (catalogueJson as { species: SpeciesEntry[] }).species

export const rules: RuleEntry[] = (rulesJson as { rules: RuleEntry[] }).rules

export const sources: Record<string, SourceEntry> =
  (sourcesJson as { sources: Record<string, SourceEntry> }).sources

export function rulesForSpecies(speciesId: string): RuleEntry[] {
  return rules.filter((r) => r.species_id === speciesId)
}

/** GN 167/2016 octopus rules — the two entries the page must surface first. */
export const OCTOPUS_SPECIES_ID = 'octopus_cyanea'

/** Species ordered octopus-first so GN 167/2016 leads the browser. */
export const orderedSpecies: SpeciesEntry[] = [
  ...species.filter((s) => s.species_id === OCTOPUS_SPECIES_ID),
  ...species.filter((s) => s.species_id !== OCTOPUS_SPECIES_ID),
]
