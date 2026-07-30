/* Transport pillar — frontend mirror of backend/app/pillars/transport/module.py.
 *
 * Same convention as pillars/types.ts: kept in sync BY HAND so the frontend
 * builds with the backend down. If module.py changes shape after S4, that is a
 * decision-log event and this file changes in the same commit.
 */
import type { PillarResult } from '../types'

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
  /** Great-circle distance from the port, in nautical miles. NOTE: this is the
   *  ONLY spatial field per vessel — AIS bearings are not exposed, which is why
   *  the chart plots ranges on a schematic approach line rather than pretending
   *  to know positions. */
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

/** 'model' = grounded prose from the inference provider; anything else means
 *  the deterministic assembly served instead and narrative_note says why. */
export type NarrativeSource = 'model' | 'deterministic_fallback'

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
