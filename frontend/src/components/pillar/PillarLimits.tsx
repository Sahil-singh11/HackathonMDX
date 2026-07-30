/* PillarLimits — collapsible "What this doesn't cover".
 *
 * Props
 *   summary    string      REQUIRED. One line, shown on the trigger, visible
 *                          while collapsed. The single most important prop here.
 *   children?  ReactNode   the full caveat.
 *   items?     string[]    rendered as a list if you have no prose.
 *   title?     string      default "What this doesn't cover".
 *
 * FOLDED, NEVER HIDDEN — and `summary` is what makes that true. A collapsed
 * section whose trigger says only "What this doesn't cover" has hidden the
 * caveat behind a click and kept the reassuring part visible. A trigger that says
 * "Forecast, not a survey. Excludes seabed and grid access." has folded it: the
 * reader already knows the shape of the limitation and clicks for detail.
 *
 * That is why `summary` is required rather than optional. It is the one prop in
 * this module the type system will not let a page author skip, because it is the
 * one whose absence would make the page quietly overclaim.
 *
 * Write the summary as the LIMIT, not as an apology, and never paraphrase a
 * backend `coverage_note` or `scope_note` into something softer — those are
 * rendered verbatim in this app. If the note is already one line, pass it.
 */
import type { ReactNode } from 'react'
import { Collapsible } from './Collapsible'

export function PillarLimits({
  summary, children, items, title = "What this doesn't cover",
}: {
  summary: string
  children?: ReactNode
  items?: string[]
  title?: string
}) {
  return (
    <Collapsible title={title} summary={summary} defaultOpen={false}>
      {children}
      {items && items.length > 0 && (
        <ul className="lkp-limits__list">
          {items.map((it) => <li key={it}>{it}</li>)}
        </ul>
      )}
    </Collapsible>
  )
}
