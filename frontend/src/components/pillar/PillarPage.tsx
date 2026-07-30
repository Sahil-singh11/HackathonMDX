/* PillarPage — the wrapper. Resolves the accent, renders the header, and places
 * every section in the one fixed order.
 *
 * Props
 *   pillar      PillarId      which pillar. Resolves the accent (see accents.css).
 *   pillarName  string        the h1.
 *   purpose     string        one plain-language sentence for the header.
 *   status      PillarStatus  'live' | 'cached' | 'not-in-build'.
 *   answer      ReactNode     REQUIRED — a <PillarAnswer>.
 *   figures?    ReactNode     a <PillarFigures>.
 *   visual?     ReactNode     a <PillarVisual>.
 *   detail?     ReactNode     a <PillarDetail>.
 *   method?     ReactNode     a <PillarMethod>.
 *   limits?     ReactNode     a <PillarLimits>.
 *   source?     ReactNode     a <PillarSource>.
 *   back?       ReactNode     optional link rendered above the header.
 *   statusLabels?  translation override, passed through to PillarHeader.
 *
 * SLOTS ARE NAMED PROPS, NOT children, AND THAT IS THE WHOLE DESIGN.
 *
 *   answer -> figures -> visual -> detail -> method -> limits -> source
 *   plain language, then numbers, then methodology, then caveats, then provenance
 *
 * With `children` a page author controls the order, and six authors produce six
 * orders — which is why the existing pages feel unfinished. Here the order is a
 * property of the framework: it cannot be overridden without editing this file,
 * and a section left out simply does not render. Reordering is not a prop.
 *
 * `answer` IS THE ONLY REQUIRED SLOT. A pillar page that cannot say in one
 * sentence what it tells the user does not have a reason to exist yet, so the
 * type system asks for that sentence before it accepts anything else. Everything
 * below it is optional because not every pillar has a map, a table or a formula.
 *
 * ACCENT RESOLUTION is a `data-pillar` attribute, not an inline style: the six
 * hues are mixed from semantic tokens in CSS, so they follow theme repoints —
 * including the two themes that deliberately collapse them (see accents.css).
 *
 * `.lk-scope` opts the subtree into the semantic tokens and the new typography.
 * Without it this page would inherit the legacy palette from styles.css.
 *
 * NOTHING DEVELOPER-FACING RENDERS FROM THIS MODULE. No endpoint lists, file
 * paths, task references, version strings, owner names or HTTP status codes, in
 * any of these components. A reader is told what the page says and where the data
 * came from — not how it is wired.
 */
import type { ReactNode } from 'react'
import { PillarHeader } from './PillarHeader'
import type { PillarId, PillarStatus } from './types'
import './pillar.css'

export function PillarPage({
  pillar, pillarName, purpose, status, statusLabels,
  answer, figures, visual, detail, method, limits, source, back,
}: {
  pillar: PillarId
  pillarName: string
  purpose: string
  status: PillarStatus
  statusLabels?: Partial<Record<PillarStatus, string>>
  answer: ReactNode
  figures?: ReactNode
  visual?: ReactNode
  detail?: ReactNode
  method?: ReactNode
  limits?: ReactNode
  source?: ReactNode
  back?: ReactNode
}) {
  return (
    <div className="lk-scope lkp-page" data-pillar={pillar}>
      {back && <div className="lkp-page__back">{back}</div>}

      <PillarHeader
        pillarName={pillarName}
        purpose={purpose}
        status={status}
        statusLabels={statusLabels}
      />

      {/* The fixed order. Do not reorder these lines to suit one page. */}
      {answer}
      {figures}
      {visual}
      {detail}
      {method}
      {limits}
      {source}
    </div>
  )
}
