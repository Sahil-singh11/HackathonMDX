/* Shared row shape for the catch log (Lane B).
 *
 * /api/catches returns Record<string, unknown>[]; this narrows it once, at the
 * page boundary, so components below are typed.
 */

export interface CatchRow {
  id: string
  species_id: string
  count: number
  capture_date: string
  measured_length_cm: number | null
  fishing_area: string
  legal_status: string
  /** Present only on locally queued records; server records are already synced. */
  pending?: boolean
}

export type SyncFilter = 'all' | 'synced' | 'pending'

export function toCatchRow(raw: Record<string, unknown>): CatchRow {
  return {
    id: String(raw.id ?? ''),
    species_id: String(raw.species_id ?? ''),
    count: Number(raw.count ?? 1),
    capture_date: String(raw.capture_date ?? ''),
    measured_length_cm: raw.measured_length_cm == null ? null : Number(raw.measured_length_cm),
    fishing_area: String(raw.fishing_area ?? ''),
    legal_status: String(raw.legal_status ?? 'unknown'),
  }
}
