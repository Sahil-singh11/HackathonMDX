/* PillarMethod — collapsible "How these numbers are produced". Holds formulas.
 *
 * Props
 *   children   ReactNode          prose, if the method needs any.
 *   formulas?  PillarFormula[]    { name, expression, note? } — rendered mono.
 *   title?     string             default 'How these numbers are produced'.
 *   summary?   string             one line on the trigger.
 *
 * Collapsed by default on every viewport, unlike PillarDetail. Method is the third
 * thing a reader wants, after the answer and the figures, and only some readers
 * want it at all — but the ones who do are usually the ones deciding whether to
 * trust the page, so it is never further away than one click.
 *
 * FORMULAS ARE PRINTED SO A READER CAN RE-DERIVE THE FIGURE RATHER THAN TRUST IT.
 * That is the entire purpose of this section, and it is why `expression` is mono:
 * these are read character by character, not skimmed.
 *
 * `name` IS A PLAIN LABEL, NOT A FIELD NAME. "Wave power density", not
 * "wave_power_kw_per_m". The framework forbids field names, file paths, endpoint
 * lists and version strings anywhere in these components; a formula's identity is
 * its maths, which is in `expression`.
 */
import type { ReactNode } from 'react'
import { Collapsible } from './Collapsible'

export interface PillarFormula {
  /** Plain-language name of what this computes. */
  name: string
  /** The expression itself, with units. Rendered mono. */
  expression: string
  /** Optional one-line caveat about the expression. */
  note?: string
}

export function PillarMethod({
  children, formulas, title = 'How these numbers are produced', summary,
}: {
  children?: ReactNode
  formulas?: PillarFormula[]
  title?: string
  summary?: string
}) {
  return (
    <Collapsible title={title} summary={summary} defaultOpen={false}>
      {children}
      {formulas && formulas.length > 0 && (
        <dl className="lkp-method__list">
          {formulas.map((f) => (
            <div className="lkp-method__item" key={f.name}>
              <dt className="lkp-method__name">{f.name}</dt>
              <dd className="lkp-method__body">
                <code className="lkp-method__expr">{f.expression}</code>
                {f.note && <span className="lkp-method__note">{f.note}</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </Collapsible>
  )
}
