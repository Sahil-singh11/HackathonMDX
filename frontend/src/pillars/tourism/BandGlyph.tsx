/* Workstream 2 — the marker glyphs, in the DOM.
 *
 * These are the SAME four shapes SiteChart paints on the canvas. That is the
 * whole job: the canvas is aria-hidden decoration, so the shape ↔ band mapping
 * has to exist somewhere a screen reader and a Sunlight-theme user can reach.
 * Rendering it here means the legend, the site buttons and the chart cannot
 * disagree about what a triangle means.
 *
 * Colour is carried by `currentColor`, set from a semantic token by the
 * .tou-glyph--* class in tourism.css — so no colour literal appears here
 * either, and the glyph re-themes with everything else.
 */
import type { Band } from './chartGeometry'

interface Props {
  band: Band
  size?: number
}

/** Decorative: every glyph is rendered next to its own text label. */
export default function BandGlyph({ band, size = 20 }: Props) {
  const c = size / 2
  const r = size * 0.32
  const stroke = { stroke: 'var(--border-strong)', strokeWidth: 1.4 }

  return (
    <svg
      className={`tou-glyph tou-glyph--${band}`}
      width={size} height={size} viewBox={`0 0 ${size} ${size}`}
      aria-hidden="true" focusable="false"
    >
      {band === 'good' && <circle cx={c} cy={c} r={r} fill="currentColor" style={stroke} />}
      {band === 'fair' && (
        <rect
          x={c - r * 0.86} y={c - r * 0.86} width={r * 1.72} height={r * 1.72}
          fill="currentColor" style={stroke}
        />
      )}
      {band === 'poor' && (
        <polygon
          points={`${c},${c + r * 1.15} ${c + r * 1.08},${c - r * 0.72} ${c - r * 1.08},${c - r * 0.72}`}
          fill="currentColor" style={stroke}
        />
      )}
      {band === 'unknown' && (
        <>
          <circle cx={c} cy={c} r={r} fill="none" style={{ stroke: 'currentColor', strokeWidth: 2 }} />
          <line
            x1={c - r * 0.62} y1={c} x2={c + r * 0.62} y2={c}
            style={{ stroke: 'currentColor', strokeWidth: 2 }}
          />
        </>
      )}
    </svg>
  )
}

/** The dashed collar drawn around sites inside a marine protected area. */
export function ProtectedGlyph({ size = 20 }: { size?: number }) {
  const c = size / 2
  return (
    <svg
      className="tou-glyph tou-glyph--protected"
      width={size} height={size} viewBox={`0 0 ${size} ${size}`}
      aria-hidden="true" focusable="false"
    >
      <circle
        cx={c} cy={c} r={size * 0.38} fill="none"
        style={{ stroke: 'currentColor', strokeWidth: 1.4, strokeDasharray: '3 3' }}
      />
      <circle cx={c} cy={c} r={size * 0.16} fill="currentColor" />
    </svg>
  )
}
