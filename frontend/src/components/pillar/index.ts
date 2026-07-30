/**
 * Pillar page framework — barrel. Import from here, never from the files:
 *
 *   import { PillarPage, PillarAnswer, PillarFigures } from '../components/pillar'
 *
 * WHAT THIS IS. One layout every pillar page is built from, so six pages stop
 * inventing six layouts. Compose the sections and hand them to PillarPage as
 * named slots; PillarPage places them in the fixed order:
 *
 *   answer -> figures -> visual -> detail -> method -> limits -> source
 *
 * Plain language first, numbers second, methodology third, caveats fourth,
 * provenance last. That order is enforced by PillarPage, not by the caller.
 *
 * `answer` is the only required slot. See PillarAnswer for why.
 *
 * LABELS ARE ENGLISH-DEFAULTED PROPS, NOT i18n KEYS. Every visible string in this
 * module is a prop with an English default, so the framework has no dependency on
 * the translation catalogue and adding it needs no edit to a shared file that
 * three people are working in. A converting page should pass `useT()` values
 * through `title`, `summary`, `statusLabels` and `kindLabels`; ExamplePillarPage
 * shows the shape. Untranslated defaults are visible, which is the failure mode
 * we want — a missing translation looks like English, not like a raw key.
 *
 * NOT EXPORTED: Collapsible. Use PillarDetail / PillarMethod / PillarLimits,
 * which carry the right heading and the right default open state for their
 * content.
 *
 * `PillarDetail` here is a SECTION CONTAINER. The route component of the same
 * name lives in `pillars/PillarDetail.tsx`. Different folders, no conflict; alias
 * on import if a file ever needs both.
 */
export { PillarPage } from './PillarPage'
export { PillarHeader } from './PillarHeader'
export { PillarAnswer } from './PillarAnswer'
export { PillarFigures } from './PillarFigures'
export { PillarVisual } from './PillarVisual'
export { PillarDetail } from './PillarDetail'
export { PillarMethod, type PillarFormula } from './PillarMethod'
export { PillarLimits } from './PillarLimits'
export { PillarSource } from './PillarSource'
export type { PillarId, PillarStatus, PillarDataKind, PillarFigure } from './types'
