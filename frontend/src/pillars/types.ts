/* Workstream 2 — pillar shell types.
 *
 * These mirror the backend contract frozen at Task 4a (sync point S4):
 *   backend/app/pillars/provenance.py  -> DataProvenance, DataKind
 *   backend/app/pillars/base.py        -> SourceDescriptor, PillarResult
 *   backend/app/pillars/registry.py    -> PillarDescriptor
 *
 * Kept in sync by hand, deliberately: generating them would couple the frontend
 * build to a running backend, and this app must build with the backend down.
 * If a signature changes after S4 it needs a decision-log entry, so drift is a
 * reviewable event rather than a silent break.
 */

/** live | cached | sample | synthetic — see provenance.py for the exact meanings. */
export type DataKind = 'live' | 'cached' | 'sample' | 'synthetic'

/**
 * The mandatory honesty block on every pillar result.
 *
 * `model_provider` and `coverage_note` are min_length=1 on the backend, so a
 * result that cannot say where its data came from or what it does not cover is
 * invalid by construction. The UI must therefore always have something to
 * render for both — if either is empty, that is a backend contract violation
 * and the badge says so rather than hiding it.
 */
export interface DataProvenance {
  source_name: string
  source_url: string | null
  /** ISO 8601. */
  retrieved_at: string
  data_kind: DataKind
  /** Inference provider that served the model step (mirrors X-Inference-Provider). */
  model_provider: string
  /** What this data does NOT cover. Mandatory, never empty, never hidden. */
  coverage_note: string
}

export interface SourceDescriptor {
  name: string
  url: string | null
  description: string
  /** A source stays "candidate" until its owner has seen a real response from it. */
  status: 'verified' | 'candidate' | 'none'
}

export interface PillarDescriptor {
  pillar_id: string
  /** Government naming, verbatim — do not shorten or restyle it. */
  pillar_name: string
  status: 'live' | 'registered'
  enabled: boolean
  implemented: boolean
  owner: string
  description: string
  sources: SourceDescriptor[]
  endpoints: string[]
}

export interface PillarsResponse {
  pillars: PillarDescriptor[]
  count: number
  note: string
}

/** Base shape of any pillar's result — provenance is required on the base. */
export interface PillarResult {
  pillar_id: string
  generated_at: string
  provenance: DataProvenance
}

/**
 * Response from the optional per-pillar provenance probe
 * (GET /api/pillars/{id}/provenance).
 *
 * The probe runs the pillar's fetch() only — no inference — so `data_kind`,
 * `source_name` and `coverage_note` are real while `model_provider` is the
 * literal "not-invoked". `would_use_provider` names the provider that WOULD have
 * served, which is not the same claim as having served.
 *
 * A pillar that has not adopted the convention returns 404. Render that as an
 * absence; never substitute a guessed data_kind.
 */
export interface PillarProbe {
  pillar_id: string
  probe: true
  provenance: DataProvenance
  would_use_provider: string
  note: string
}
