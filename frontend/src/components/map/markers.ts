/**
 * Marker icons and label de-collision for the shared map.
 *
 * WHY divIcon AND NOT L.icon. L.icon needs image URLs, and Leaflet's default
 * marker sprite is the classic bundler trap: it resolves its own PNG paths
 * relative to the CSS, which Vite rewrites, so you get broken images or a
 * silently missing marker. A divIcon is just HTML, so there is no asset to lose
 * — and because the SVG is inline it inherits `currentColor` and our theme
 * tokens for free, which an <img> never could.
 *
 * SHAPE CARRIES THE STATUS, colour only reinforces it. The vocabulary is fixed
 * across every map in the app so a shape means the same thing everywhere:
 *   circle    good / normal / active
 *   square    caution / degraded / pending
 *   triangle  poor / alert / blocked
 *   diamond   informational, no status
 */
import L from 'leaflet'

export type MarkerStatus = 'good' | 'caution' | 'poor' | 'info'
export type MarkerShape = 'circle' | 'square' | 'triangle' | 'diamond'

const SHAPE_FOR_STATUS: Record<MarkerStatus, MarkerShape> = {
  good: 'circle',
  caution: 'square',
  poor: 'triangle',
  info: 'diamond',
}

/** Geometry only — colour comes from a CSS class so themes drive it. */
function shapePath(shape: MarkerShape): string {
  switch (shape) {
    case 'square':
      return '<rect x="5" y="5" width="18" height="18" rx="2" />'
    case 'triangle':
      return '<path d="M14 4 L25 23 L3 23 Z" />'
    case 'diamond':
      return '<path d="M14 3 L25 14 L14 25 L3 14 Z" />'
    case 'circle':
    default:
      return '<circle cx="14" cy="14" r="9" />'
  }
}

export interface MarkerIconOptions {
  status: MarkerStatus
  shape?: MarkerShape
  /** Small number badge. The full label lives in the tooltip and the side list. */
  badge?: number
  selected?: boolean
}

/**
 * Build a divIcon. The number badge is the ONLY text drawn on the map: Leaflet
 * has no collision avoidance, so permanent name tooltips overlap into mush the
 * moment two sites are close. Names live in the tooltip (hover + keyboard
 * focus) and in the side list.
 */
export function buildMarkerIcon({ status, shape, badge, selected }: MarkerIconOptions): L.DivIcon {
  const glyph = shape ?? SHAPE_FOR_STATUS[status]
  const cls = `lkmap-marker lkmap-marker--${status}${selected ? ' is-selected' : ''}`
  const html = `
<span class="${cls}">
  <svg viewBox="0 0 28 28" width="28" height="28" aria-hidden="true" focusable="false">
    ${shapePath(glyph)}
  </svg>
  ${badge != null ? `<span class="lkmap-marker__badge">${badge}</span>` : ''}
</span>`
  return L.divIcon({
    html,
    className: 'lkmap-divicon', // strip Leaflet's default white box
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    tooltipAnchor: [0, -14],
  })
}

/** North arrow, drawn as a Leaflet control rather than an overlay marker. */
export function northArrowHtml(label: string): string {
  return `
<div class="lkmap-north" title="${label}">
  <svg viewBox="0 0 24 34" width="24" height="34" aria-hidden="true" focusable="false">
    <path d="M12 1 L18 15 L12 12 L6 15 Z" />
    <line x1="12" y1="12" x2="12" y2="30" />
  </svg>
  <span class="lkmap-north__n">N</span>
</div>`
}

/* ---------------------------------------------------------------------------
 * Badge de-collision.
 *
 * Leaflet places markers at exact coordinates and lets them overlap. Sites a few
 * hundred metres apart produce unreadable stacked badges at island zoom. Rather
 * than pull in a clustering plugin — which hides markers behind a count and
 * breaks the one-marker-per-site contract the side list depends on — this does
 * one deterministic pass: any badge closer than MIN_GAP to an already-placed one
 * is nudged along the vector away from it.
 *
 * Deliberately simple and stable: same input, same output, no animation, no
 * iteration to convergence. Markers move by a few pixels; the underlying
 * coordinate is untouched, so the shape still sits on the true position.
 * ------------------------------------------------------------------------- */

const MIN_GAP = 30 // px, slightly more than one 28px icon

export interface Placed {
  id: string
  x: number
  y: number
}

/** Returns pixel offsets keyed by marker id. Empty when nothing collides. */
export function decollide(points: Placed[]): Record<string, [number, number]> {
  const offsets: Record<string, [number, number]> = {}
  const settled: Placed[] = []

  for (const p of points) {
    let { x, y } = p
    for (const s of settled) {
      const dx = x - s.x
      const dy = y - s.y
      const dist = Math.hypot(dx, dy)
      if (dist < MIN_GAP) {
        // Push directly away from the neighbour. When two markers coincide
        // exactly, fall back to a fixed direction so the result stays stable.
        const push = MIN_GAP - dist
        const angle = dist < 0.001 ? -Math.PI / 2 : Math.atan2(dy, dx)
        x += Math.cos(angle) * push
        y += Math.sin(angle) * push
      }
    }
    settled.push({ id: p.id, x, y })
    const ox = Math.round(x - p.x)
    const oy = Math.round(y - p.y)
    if (ox !== 0 || oy !== 0) offsets[p.id] = [ox, oy]
  }
  return offsets
}
