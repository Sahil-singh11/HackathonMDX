/**
 * FigureRow — the supporting numbers under the answer.
 *
 * Capped at four by convention, not by code: a fifth figure is a sign the
 * pillar is putting its detail table in the wrong slot. Values are mono
 * (--font-data) because these are figures an officer might read aloud.
 *
 * A null value renders as "unavailable" rather than 0 or a dash. 0 is a real
 * physical claim and must never stand in for missing data.
 */
import type { ReactNode } from 'react'

export interface Figure {
  label: string
  value: number | string | null
  unit?: string
  /** Optional one-line qualifier, e.g. where the reading came from. */
  note?: ReactNode
}

export default function FigureRow({ figures, unavailableLabel = 'unavailable' }: {
  figures: Figure[]
  unavailableLabel?: string
}) {
  return (
    <dl className="pil-figures">
      {figures.map((f) => (
        <div className="pil-figure" key={f.label}>
          <dt>{f.label}</dt>
          <dd>
            {f.value == null
              ? <span className="pil-figure__na">{unavailableLabel}</span>
              : <>
                <span className="pil-figure__value">{f.value}</span>
                {f.unit && <span className="pil-figure__unit"> {f.unit}</span>}
              </>}
          </dd>
          {f.note && <p className="pil-figure__note">{f.note}</p>}
        </div>
      ))}
    </dl>
  )
}
