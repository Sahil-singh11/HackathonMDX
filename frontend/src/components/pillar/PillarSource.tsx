/* PillarSource — the footer strip: source, data-kind badge, timestamp. One line.
 *
 * Props
 *   sourceName   string          e.g. 'Open-Meteo Marine'.
 *   dataKind     PillarDataKind  'live' | 'cached' | 'sample' | 'synthetic'.
 *   retrievedAt  string          ISO timestamp. Rendered mono, plus a relative age.
 *   sourceUrl?   string          makes the name a link. Omit if there is no page.
 *   kindLabels?  partial override of the four badge labels (for translation).
 *
 * Last on the page, by the fixed order: answer, figures, visual, detail, method,
 * limits, source. Provenance is what a reader checks after they have understood
 * the answer, not before.
 *
 * ONE LINE. It wraps on a narrow screen but it never becomes a panel. The full
 * provenance block — coverage notes, which model was involved — is a different
 * component's job; this strip answers "where is this from, and how old is it?".
 *
 * VISUAL WEIGHT SCALES WITH RISK. live and cached are quiet, because they are the
 * normal trustworthy states and shouting about them trains people to ignore the
 * badge. sample and synthetic are loud, because generated numbers presented as
 * observations is the worst failure available to this app. Every kind carries an
 * icon and a word as well as a colour.
 *
 * THE TIMESTAMP IS MONO because it is the kind of thing an officer reads aloud,
 * and it is shown as well as the relative age: "25 min ago" is what a reader
 * wants, the absolute value is what they would quote.
 */
import { Beaker, Clock, FlaskConical, Radio } from 'lucide-react'
import { Badge, type BadgeTone } from '../ui'
import type { PillarDataKind } from './types'

const KIND: Record<PillarDataKind, { tone: BadgeTone; icon: typeof Radio; label: string; loud: boolean }> = {
  live: { tone: 'success', icon: Radio, label: 'Live', loud: false },
  cached: { tone: 'neutral', icon: Clock, label: 'Cached', loud: false },
  sample: { tone: 'warning', icon: Beaker, label: 'Sample', loud: true },
  synthetic: { tone: 'danger', icon: FlaskConical, label: 'Stand-in data', loud: true },
}

/** "25 min ago". Returns null for an unparseable timestamp rather than guessing. */
function relativeAge(iso: string): string | null {
  const then = Date.parse(iso)
  if (Number.isNaN(then)) return null
  const mins = Math.floor((Date.now() - then) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} h ago`
  return `${Math.floor(hours / 24)} d ago`
}

export function PillarSource({ sourceName, dataKind, retrievedAt, sourceUrl, kindLabels }: {
  sourceName: string
  dataKind: PillarDataKind
  retrievedAt: string
  sourceUrl?: string
  kindLabels?: Partial<Record<PillarDataKind, string>>
}) {
  const k = KIND[dataKind] ?? KIND.synthetic
  const Icon = k.icon
  const age = relativeAge(retrievedAt)

  return (
    <footer className={`lkp-source${k.loud ? ' lkp-source--loud' : ''}`}>
      <Badge tone={k.tone} icon={<Icon size={14} aria-hidden="true" />}>
        {kindLabels?.[dataKind] ?? k.label}
      </Badge>
      <span className="lkp-source__name">
        {sourceUrl
          ? <a href={sourceUrl} target="_blank" rel="noreferrer">{sourceName}</a>
          : sourceName}
      </span>
      <span className="lkp-source__time">
        {age && <span className="lkp-source__age">{age}</span>}
        <time className="lkp-source__stamp" dateTime={retrievedAt}>{retrievedAt}</time>
      </span>
    </footer>
  )
}
