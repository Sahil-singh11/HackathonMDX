/* PillarFigures — the 3-4 key values, under the answer.
 *
 * Props
 *   figures   PillarFigure[]   3-4 entries: { label, value, unit?, hint? }
 *   label?    string           accessible name for the group. Default "Key figures".
 *
 * Mono numerals, small-weight units, plain labels. Two columns under 768px, and
 * as many as fit above it.
 *
 * THREE OR FOUR, NOT NINE. The cap is the design: a strip that grows past four
 * stops being "the key values" and becomes the table it was meant to summarise.
 * More than four belongs in PillarDetail. Over-length input is not thrown away —
 * it renders, and warns in development, because losing a figure silently on a
 * page about real measurements would be worse than an ugly row.
 *
 * VALUES ARE MONO AND TABULAR. font-variant-numeric: tabular-nums so digits share
 * a width and the column aligns; without it "1.11" and "25.48" wander and the
 * strip reads as sloppy. Units sit at normal weight next to a semibold value, so
 * the number is what the eye lands on.
 *
 * A MISSING VALUE IS AN EM-DASH, NEVER A ZERO. Pass '—'. A zero is a reading; a
 * missing reading is not a calm sea, and this app never invents the difference.
 */
import { useEffect } from 'react'
import type { PillarFigure } from './types'

export function PillarFigures({ figures, label = 'Key figures' }: {
  figures: PillarFigure[]
  label?: string
}) {
  useEffect(() => {
    if (import.meta.env.DEV && (figures.length < 2 || figures.length > 4)) {
      // eslint-disable-next-line no-console
      console.warn(
        `[PillarFigures] ${figures.length} figures passed; this strip is designed for 3-4. `
        + 'Move the extras into PillarDetail rather than widening the strip.',
      )
    }
  }, [figures.length])

  if (figures.length === 0) return null

  return (
    <section className="lkp-figures" aria-label={label}>
      <dl className="lkp-figures__grid">
        {figures.map((f) => (
          <div className="lkp-figures__item" key={f.label}>
            <dt className="lkp-figures__label">{f.label}</dt>
            <dd className="lkp-figures__value">
              <span className="lkp-figures__number">{f.value}</span>
              {f.unit && <span className="lkp-figures__unit">{f.unit}</span>}
              {f.hint && <span className="lkp-figures__hint">{f.hint}</span>}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
