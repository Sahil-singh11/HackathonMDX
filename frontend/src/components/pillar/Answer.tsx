/**
 * Answer — the conclusion, first, in one sentence.
 *
 * The hero number is deliberately OPTIONAL and deliberately separate from the
 * sentence. A pillar that has no single defensible headline figure must be able
 * to give a sentence without one, rather than inventing a number to fill the
 * slot. And when a hero number exists it is rendered from the same value the
 * sentence quotes, never re-derived here.
 *
 * `tone` exists so an honest negative answer ("no site rates well today") reads
 * as a real finding rather than an error state. Colour is never the only signal:
 * the sentence itself always carries the meaning.
 *
 * Props:
 *   sentence  ReactNode  one sentence, no more
 *   hero?     { value, unit?, caption? }
 *   tone?     'neutral' | 'positive' | 'caution'
 */
import type { ReactNode } from 'react'

export interface HeroNumber {
  value: string | number
  unit?: string
  /** Short label under the number, e.g. the site it belongs to. */
  caption?: string
}

interface Props {
  sentence: ReactNode
  hero?: HeroNumber
  tone?: 'neutral' | 'positive' | 'caution'
}

export default function Answer({ sentence, hero, tone = 'neutral' }: Props) {
  return (
    <div className={`pil-answer pil-answer--${tone}`}>
      {hero && (
        <div className="pil-answer__hero">
          <span className="pil-answer__hero-value">
            {hero.value}
            {hero.unit && <span className="pil-answer__hero-unit">{hero.unit}</span>}
          </span>
          {hero.caption && <span className="pil-answer__hero-caption">{hero.caption}</span>}
        </div>
      )}
      <p className="pil-answer__sentence">{sentence}</p>
    </div>
  )
}
