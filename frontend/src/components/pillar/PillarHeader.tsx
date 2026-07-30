/* PillarHeader — title, one-line purpose, accent rule, one status chip.
 *
 * Props
 *   pillarName  string        the pillar's own name. Rendered as the page's h1.
 *   purpose     string        ONE plain-language sentence: what this page tells
 *                             you. Not a paragraph — see below.
 *   status      PillarStatus  'live' | 'cached' | 'not-in-build'.
 *   statusLabels?  partial override of the three chip labels (for translation).
 *
 * Rendered by PillarPage. A page author does not use this directly, and does not
 * add a second h1 — there is exactly one per page and this is it.
 *
 * "NOT A PARAGRAPH" IS ENFORCED, NOT REQUESTED. `purpose` is typed as a string
 * rather than ReactNode, so no one can pass two <p>s, and the CSS clamps it to
 * two lines with a max width. The old pillar pages each opened with a block of
 * explanation, which is exactly why they read as unfinished: the reader had to
 * get through our description of the feature before reaching the feature.
 *
 * ONE CHIP. Not a row of badges. Provenance detail belongs in PillarSource at the
 * foot of the page; the header answers only "is what I am looking at current?".
 * Each chip carries an icon as well as a colour, because colour is never the only
 * signal in this app.
 */
import { CircleDot, Clock, Minus } from 'lucide-react'
import { Badge, type BadgeTone } from '../ui'
import type { PillarStatus } from './types'

const STATUS: Record<PillarStatus, { tone: BadgeTone; icon: typeof CircleDot; label: string }> = {
  live: { tone: 'success', icon: CircleDot, label: 'Live' },
  cached: { tone: 'neutral', icon: Clock, label: 'Cached' },
  /* Neutral, never danger. A pillar this build does not implement is a scope
     decision, not a fault, and styling it red would say otherwise. */
  'not-in-build': { tone: 'neutral', icon: Minus, label: 'Not in this build' },
}

export function PillarHeader({ pillarName, purpose, status, statusLabels }: {
  pillarName: string
  purpose: string
  status: PillarStatus
  statusLabels?: Partial<Record<PillarStatus, string>>
}) {
  const s = STATUS[status] ?? STATUS.cached
  const Icon = s.icon

  return (
    <header className="lkp-header">
      <div className="lkp-header__row">
        <h1 className="lkp-header__title">{pillarName}</h1>
        <Badge tone={s.tone} icon={<Icon size={14} aria-hidden="true" />}>
          {statusLabels?.[status] ?? s.label}
        </Badge>
      </div>
      <p className="lkp-header__purpose">{purpose}</p>
      {/* The accent rule is the only place the pillar's hue appears at size.
          Decorative, so it is hidden from assistive tech. */}
      <div className="lkp-header__rule" aria-hidden="true" />
    </header>
  )
}
