/**
 * Foldable — Detail / Method / Limits sections.
 *
 * A real <details>/<summary>, not a JS accordion. That matters here beyond
 * taste: the content stays in the DOM, so browser find-in-page reaches it, it
 * is keyboard operable and screen-reader announced with no code from us, and it
 * still works if the JS bundle fails. For sections that carry mandatory
 * disclosures, "collapsed" must never mean "not present".
 *
 * `tone="limits"` gives the caveat section a visible edge so it reads as a
 * standing qualification rather than optional extra reading.
 */
import type { ReactNode } from 'react'

interface Props {
  title: string
  children: ReactNode
  /** Short count/summary shown next to the title, e.g. "5 vessels". */
  hint?: string
  tone?: 'default' | 'limits' | 'method'
  /** Open on first render. Default false — the point is a calm page. */
  defaultOpen?: boolean
}

export default function Foldable({ title, children, hint, tone = 'default', defaultOpen = false }: Props) {
  return (
    <details className={`pil-fold pil-fold--${tone}`} open={defaultOpen}>
      <summary className="pil-fold__summary">
        <span className="pil-fold__title">{title}</span>
        {hint && <span className="pil-fold__hint">{hint}</span>}
      </summary>
      <div className="pil-fold__body">{children}</div>
    </details>
  )
}
