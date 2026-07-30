/**
 * BarComparison — ranked horizontal bars for comparing candidate sites.
 *
 * Pure CSS widths over real values, no charting library and no canvas: the
 * bundle already carries Leaflet for maps, and a bar chart does not justify a
 * second dependency.
 *
 * ACCESSIBILITY. The bars are decoration. The real content is a definition list
 * with the value in text, so a screen reader gets the numbers in order without
 * touching the visual, and the same is true in Sunlight where the fills are
 * flattened. Each row also carries an explicit `aria-label` combining name and
 * value, so the list reads as pairs rather than two disconnected columns.
 *
 * Bars are scaled against the LARGEST value present, and that is stated in the
 * caption — a reader must not infer an absolute scale from a relative bar.
 *
 * Props:
 *   items    { id, label, value, unit?, detail?, highlight? }[]
 *   caption  string  what the bar length means
 */
export interface BarItem {
  id: string
  label: string
  value: number | null
  unit?: string
  /** Secondary text, e.g. region or distance from shore. */
  detail?: string
  /** The winning item, emphasised in the same way the answer names it. */
  highlight?: boolean
}

interface Props {
  items: BarItem[]
  caption: string
  unavailableLabel?: string
}

export default function BarComparison({ items, caption, unavailableLabel = 'unavailable' }: Props) {
  const values = items.map((i) => i.value ?? 0)
  const max = Math.max(...values, 0)

  return (
    <figure className="pil-bars">
      <dl className="pil-bars__list">
        {items.map((item) => {
          const pct = max > 0 && item.value != null ? (item.value / max) * 100 : 0
          return (
            <div
              key={item.id}
              className={`pil-bars__row${item.highlight ? ' is-top' : ''}`}
              aria-label={`${item.label}: ${item.value ?? unavailableLabel}${item.unit ? ` ${item.unit}` : ''}`}
            >
              <dt className="pil-bars__label">
                {item.label}
                {item.detail && <span className="pil-bars__detail">{item.detail}</span>}
              </dt>
              <dd className="pil-bars__value">
                {/* Decoration only — the number beside it is the content. */}
                <span className="pil-bars__track" aria-hidden="true">
                  <span className="pil-bars__fill" style={{ width: `${pct}%` }} />
                </span>
                <span className="pil-bars__number">
                  {item.value == null
                    ? <span className="pil-figure__na">{unavailableLabel}</span>
                    : <>{item.value}{item.unit && <span className="pil-figure__unit"> {item.unit}</span>}</>}
                </span>
              </dd>
            </div>
          )
        })}
      </dl>
      <figcaption className="pil-bars__caption">{caption}</figcaption>
    </figure>
  )
}
