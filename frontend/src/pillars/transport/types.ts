/* Transport pillar — frontend mirror of backend/app/pillars/transport/module.py.
 *
 * Same convention as pillars/types.ts: kept in sync BY HAND so the frontend
 * builds with the backend down. If module.py changes shape after S4, that is a
 * decision-log event and this file changes in the same commit.
 */
import type { PillarResult } from '../types'

/* ==========================================================================
 * APPROACH BRIEF — the pillar's primary surface, from LIVE marine data.
 *
 * Everything here is either a real Open-Meteo reading or a band computed from
 * one in Python (transport/transit.py). Nothing is synthetic, which is the
 * whole reason this replaced the arrivals brief as what the UI leads with.
 * ========================================================================== */

/** Fixed-threshold band. `unknown` means a required reading was missing — it is
 *  never a stand-in for "probably fine". */
export type Band = 'good' | 'moderate' | 'poor' | 'unknown'

export interface CraftWindow {
  /** e.g. "Small open craft (artisanal fishing boat)". */
  craft: string
  wave_band: Band
  wind_band: Band
  /** Weakest link of the two — a calm sea under a gale is not a good window. */
  overall: Band
  /** Which reading decided `overall`, so a surprising band is explainable. */
  limiting_factor: string
  /** The actual numeric thresholds, printed so a reader can disagree with them. */
  thresholds_note: string
}

export interface ApproachBrief extends PillarResult {
  port: PortDescriptor
  /** Observation time from the upstream forecast, not our request time. */
  observed_at: string | null
  wave_height_m: number | null
  wave_period_s: number | null
  swell_height_m: number | null
  swell_period_s: number | null
  wind_speed_kmh: number | null
  wind_gusts_kmh: number | null
  sea_surface_temperature_c: number | null
  crafts: CraftWindow[]
  /** Long period + real height: a slow heave a small boat feels disproportionately. */
  long_swell_flag: boolean
  long_swell_note: string
  /** True when any input was missing, so some bands are `unknown`. */
  incomplete: boolean
  narrative: string
  narrative_source: NarrativeSource
  narrative_note: string
  advisory: boolean
  scope_note: string
}

/* ==========================================================================
 * ARRIVALS BRIEF — retained, but no longer surfaced in the UI.
 *
 * The endpoint still exists and is still honest (`data_kind: "synthetic"`),
 * because terrestrial AIS has no receiver within range of Mauritius and
 * satellite AIS is a paid product. What changed is that the app no longer
 * DISPLAYS generated vessels. Types kept so the endpoint stays typed for
 * anyone who calls it directly.
 * ========================================================================== */

export interface ArrivalEntry {
  /** The frozen <Table> is generic over Record<string, unknown> so it can read
   *  a cell by column key; an interface without an index signature does not
   *  satisfy that constraint. Declared here rather than cast at the call site,
   *  which would silence the check instead of satisfying it. */
  [key: string]: unknown
  mmsi: number
  /** null when the vessel sent positions but no static data. */
  vessel_name: string | null
  /** false = position-only contact: name/type/destination genuinely unknown. */
  identity_known: boolean
  vessel_type: string
  nav_status: string
  destination_reported: string | null
  /** ISO 8601 — self-reported over AIS, not a validated prediction. */
  reported_eta_utc: string
  hours_to_reported_eta: number
  /** Great-circle distance from the port, in nautical miles. */
  distance_nm: number
  speed_knots: number | null
  draught_m: number | null
  last_seen_utc: string
}

export interface CongestionSummary {
  vessels_tracked: number
  under_way: number
  at_anchor: number
  moored: number
  other_or_unknown_status: number
  within_approach_radius: number
  approach_radius_nm: number
  identity_unknown: number
  /** Verbatim honesty note about how the tally was made. Render as-is. */
  note: string
}

export interface PortDescriptor {
  name: string
  unlocode: string
  latitude: number
  longitude: number
}

export interface TransportConditions {
  location: string
  source: string
  mock: boolean
  wave_height_m: number | null
  swell_height_m: number | null
  swell_period_s: number | null
  sea_surface_temperature_c: number | null
}

/**
 * Which rung produced the narrative.
 *
 *   'model'                  a fresh provider call wrote it, and it passed
 *                            narrative_is_grounded plus the number firewall
 *   'cached'                 that same already-grounded prose, reused from the
 *                            narrative cache for identical conditions instead of
 *                            paying for a second identical call
 *   'deterministic_fallback' assembled in code; narrative_note says why
 *
 * 'cached' is NOT a weaker rung than 'model' — same sentences, same checks, no new
 * call. The UI must therefore treat the two alike when it attributes authorship,
 * and must never put a mechanical-summary badge on cached text.
 */
export type NarrativeSource = 'model' | 'cached' | 'deterministic_fallback'

export interface ArrivalsBrief extends PillarResult {
  port: PortDescriptor
  window_hours: number
  expected_arrivals: ArrivalEntry[]
  expected_arrivals_count: number
  congestion: CongestionSummary
  conditions: TransportConditions
  narrative: string
  risk_reasoning: string
  narrative_source: NarrativeSource
  narrative_note: string
  advisory: boolean
  scope_note: string
}
