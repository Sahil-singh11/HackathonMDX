/* Workstream 2 — pillar shell barrel.
 *
 * Yadhav (WS1) and Shirish (WS3): import from here, not from the individual
 * files, so your pillar surfaces do not depend on this folder's internal layout.
 *
 *   import { ProvenanceBadge, type DataProvenance } from '../pillars'
 *
 * ProvenanceBadge renders the backend's DataProvenance block as-is. You do not
 * need to decide how to present data_kind, how loud a warning should be, or
 * where the coverage note goes — that is settled here so all six pillars read
 * the same way. Pass the block straight through from your PillarResult.
 *
 * To attach a surface to /pillars/:id, add an entry to PILLAR_SURFACES in
 * PillarDetail.tsx. That is the only edit a pillar owner should need.
 */
export { default as ProvenanceBadge } from './ProvenanceBadge'
export { default as PillarsIndex, PillarStatusBadge } from './PillarsIndex'
export { default as PillarDetail, PILLAR_SURFACES } from './PillarDetail'
export { BADGE_EXAMPLES, FIXTURE_NOTE, FIXTURE_PILLARS } from './fixture'
export type {
  DataKind, DataProvenance, PillarDescriptor, PillarResult, PillarsResponse, SourceDescriptor,
} from './types'
