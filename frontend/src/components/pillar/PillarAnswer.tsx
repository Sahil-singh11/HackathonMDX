/* PillarAnswer — the hero, and the most important component in this module.
 *
 * Props
 *   sentence     string     ONE plain-language sentence: the answer this pillar
 *                           gives. Written for a fisher or an officer, not for us.
 *   value        ReactNode  the single hero number.
 *   unit?        string     rendered at small weight beside the value.
 *   valueLabel?  string     what the number measures. Without it a big number is
 *                           decoration, so pass it unless the sentence says it.
 *   tone?        'accent' | 'plain'   'plain' drops the tint (default 'accent').
 *
 * THE POINT OF THE WHOLE FRAMEWORK. Every pillar must lead with what it actually
 * tells the user, in words, before any table or figure. The old pages led with a
 * grid of readings, which meant the reader had to do the interpreting — the app
 * had the data and made them derive the answer from it.
 *
 * `sentence` is a plain string, and there is exactly one `value`. Both limits are
 * deliberate. A ReactNode would let a page smuggle a table in here, and a second
 * number would immediately raise "which of these is the answer?" — the question
 * this component exists to settle.
 *
 * The sentence comes FIRST in the DOM as well as visually, so a screen reader
 * also gets the answer before the number.
 *
 * NO CONFIDENCE PERCENTAGES. If the answer is model-derived, say so with a band
 * (low / moderate / high) in the sentence itself. This app never shows an
 * invented percentage, and this component gives it nowhere to live.
 *
 * The hero number uses --font-display, not --font-data: tokens.css assigns
 * display to "page titles and big numbers only", and this is the big number.
 * Aligned columns of values are PillarFigures' job, and those are mono.
 */
import type { ReactNode } from 'react'

export function PillarAnswer({ sentence, value, unit, valueLabel, tone = 'accent' }: {
  sentence: string
  value: ReactNode
  unit?: string
  valueLabel?: string
  tone?: 'accent' | 'plain'
}) {
  return (
    <section className={`lkp-answer lkp-answer--${tone}`} aria-labelledby="lkp-answer-h">
      {/* Visually hidden: the sentence below is the real heading for sighted
          readers, but the landmark still needs a name. */}
      <h2 id="lkp-answer-h" className="lkp-sr-only">In short</h2>
      <p className="lkp-answer__sentence">{sentence}</p>
      <p className="lkp-answer__figure">
        <span className="lkp-answer__value">{value}</span>
        {unit && <span className="lkp-answer__unit">{unit}</span>}
      </p>
      {valueLabel && <p className="lkp-answer__label">{valueLabel}</p>}
    </section>
  )
}
