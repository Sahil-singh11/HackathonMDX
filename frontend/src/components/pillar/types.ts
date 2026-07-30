/* Shared types for the pillar page framework.
 *
 * Kept in one file so a page author imports types from the same place as the
 * components, and so the pillar id list has exactly one definition — the accent
 * CSS keys off these strings, and a typo would silently produce no accent.
 */

/** The six national blue-economy pillars. Drives accent resolution. */
export type PillarId =
  | 'fisheries'
  | 'shipping'
  | 'tourism'
  | 'energy'
  | 'finance'
  | 'biotech'

/**
 * What a page is showing right now.
 *
 * `not-in-build` is the honest state for a pillar this build does not implement.
 * It is NOT an error and must never be styled as one — offline and unbuilt are
 * both expected states in this app.
 */
export type PillarStatus = 'live' | 'cached' | 'not-in-build'

/**
 * Provenance of the numbers on the page, mirroring the backend's `data_kind`.
 *
 * The brief for this framework named three (live / cached / synthetic).
 * `sample` is included because the backend genuinely emits it, and a page author
 * hitting it should not have to widen this union mid-conversion. `synthetic` and
 * `sample` are both styled loudly on purpose: presenting generated numbers as
 * observations is the worst thing this platform could do.
 */
export type PillarDataKind = 'live' | 'cached' | 'sample' | 'synthetic'

/** One value in the figures strip. */
export interface PillarFigure {
  /** Plain-language label. Not a field name — "Wave height", not "wave_height_m". */
  label: string
  /** The number itself. Rendered mono and tabular. Pass an em-dash for missing. */
  value: string | number
  /** Unit, rendered at small weight next to the value. */
  unit?: string
  /** Optional one-line qualifier under the value. */
  hint?: string
}
