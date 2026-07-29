/**
 * Procedural nautical-chart geometry and the time-of-day sky model.
 *
 * Everything here is generated from numbers in this file — there are no image
 * assets, no fetches and no fonts to download, so the whole scene renders with
 * the device in airplane mode.
 *
 * Colour NEVER appears as a literal here. Every value is read from a CSS custom
 * property at runtime via readToken(), so the three themes drive the chart for
 * free and nothing can drift out of sync with styles/tokens.css.
 */

/* ------------------------------------------------------------------ colour */

export interface RGB { r: number; g: number; b: number; a?: number }

/** Reads a CSS custom property off <html> and parses it to RGB. */
export function readToken(name: string, fallback: RGB = { r: 0, g: 0, b: 0 }): RGB {
  if (typeof window === 'undefined') return fallback
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return parseColor(raw) ?? fallback
}

export function parseColor(raw: string): RGB | null {
  if (!raw) return null
  if (raw.startsWith('#')) {
    const h = raw.slice(1)
    const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
    if (full.length < 6) return null
    return {
      r: parseInt(full.slice(0, 2), 16),
      g: parseInt(full.slice(2, 4), 16),
      b: parseInt(full.slice(4, 6), 16),
      a: 1,
    }
  }
  const m = raw.match(/rgba?\(([^)]+)\)/)
  if (m) {
    const [r, g, b, a] = m[1].split(',').map((v) => parseFloat(v))
    // Alpha MUST survive: the --ocean-band tokens carry 0.05-0.14, and
    // discarding it turned the water into opaque slabs instead of ripples.
    return { r, g, b, a: a === undefined ? 1 : a }
  }
  return null
}

export const mix = (a: RGB, b: RGB, t: number): RGB => ({
  r: a.r + (b.r - a.r) * t,
  g: a.g + (b.g - a.g) * t,
  b: a.b + (b.b - a.b) * t,
})

export const rgba = (c: RGB, alpha: number) =>
  `rgba(${Math.round(c.r)}, ${Math.round(c.g)}, ${Math.round(c.b)}, ${alpha})`

/* --------------------------------------------------------------- sky model */

/**
 * The sky is driven by the device's ACTUAL local hour, so a fisher opening this
 * at 4am on a jetty sees a genuinely different sky than one opening it at noon.
 *
 * Anchors are token NAMES, resolved at build time so a theme switch re-reads
 * them. Between anchors we cosine-interpolate, which avoids the hard banding a
 * linear ramp gives at dawn.
 */
interface SkyAnchor { hour: number; zenith: string; horizon: string }

const SKY_ANCHORS: SkyAnchor[] = [
  { hour: 0,  zenith: '--abyss',       horizon: '--abyss' },        // deep night
  { hour: 5,  zenith: '--abyss',       horizon: '--abyss-soft' },   // pre-dawn indigo
  { hour: 7,  zenith: '--abyss-soft',  horizon: '--coral-soft' },   // dawn warming
  { hour: 12, zenith: '--foam',        horizon: '--lagoon-soft' },  // daylight
  { hour: 17, zenith: '--foam',        horizon: '--sand' },         // late afternoon
  { hour: 19, zenith: '--abyss-soft',  horizon: '--coral-deep' },   // dusk
  { hour: 24, zenith: '--abyss',       horizon: '--abyss' },        // back to night
]

/** Cosine ease — softer than linear through the dawn/dusk transitions. */
const easeCos = (t: number) => (1 - Math.cos(Math.PI * t)) / 2

export interface Sky { zenith: RGB; horizon: RGB }

export function skyForHour(hour: number): Sky {
  let i = 0
  while (i < SKY_ANCHORS.length - 2 && SKY_ANCHORS[i + 1].hour <= hour) i++
  const a = SKY_ANCHORS[i]
  const b = SKY_ANCHORS[i + 1]
  const t = easeCos(Math.min(1, Math.max(0, (hour - a.hour) / (b.hour - a.hour))))
  return {
    zenith: mix(readToken(a.zenith), readToken(b.zenith), t),
    horizon: mix(readToken(a.horizon), readToken(b.horizon), t),
  }
}

/** Relative luminance, WCAG definition. */
export function luminance(c: RGB): number {
  const f = (v: number) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4) }
  return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b)
}

export function contrast(a: RGB, b: RGB): number {
  const la = luminance(a), lb = luminance(b)
  const [hi, lo] = la > lb ? [la, lb] : [lb, la]
  return (hi + 0.05) / (lo + 0.05)
}

/**
 * Picks the legible ink for text sitting DIRECTLY on the sky.
 *
 * This exists because the sky is driven by the clock while text colour is
 * driven by the theme, so the two can disagree: at 9pm in the Day theme the
 * sky is night-navy and --text is also near-navy, which measured 1.35:1 —
 * effectively invisible. Rather than clamp the sky (which would throw away the
 * 4am case the brief cares most about), we choose between the two semantic
 * inks the theme already provides and return whichever actually wins.
 */
export function inkForSky(sky: RGB): RGB {
  const ink = readToken('--text')
  const inkInvert = readToken('--text-invert')
  return contrast(inkInvert, sky) > contrast(ink, sky) ? inkInvert : ink
}

/** Daylight fraction 0..1 — used to keep contours quiet when the sky is bright. */
export function daylight(hour: number): number {
  if (hour <= 5 || hour >= 20) return 0
  if (hour >= 9 && hour <= 16) return 1
  if (hour < 9) return (hour - 5) / 4
  return 1 - (hour - 16) / 4
}

/* ------------------------------------------------- Mauritius, procedurally */

/**
 * Mauritius in normalised space, centre (0,0), radius ~1.
 *
 * Traced coarsely from the real outline: a rounded mass with the north-west
 * bulge toward Port Louis, the flatter east coast, and the tapered southern
 * tip at Le Morne. It is intentionally low-poly — this is a chart symbol at
 * small scale, not a map, and extra vertices would only add noise.
 */
const ISLAND: Array<[number, number]> = [
  [0.05, -1.00],  // Cap Malheureux, northern tip
  [0.33, -0.92],  // north-east coast
  [0.54, -0.71],
  [0.63, -0.44],  // Belle Mare, straighter east coast
  [0.66, -0.10],
  [0.61, 0.22],
  [0.70, 0.43],   // Pointe d'Esny bulge
  [0.51, 0.58],   // Mahebourg
  [0.36, 0.61],   // Grand Port bay pulls the coast inward
  [0.21, 0.79],
  [0.00, 0.88],   // Souillac, south coast
  [-0.26, 0.92],
  [-0.47, 0.86],
  [-0.70, 0.81],  // Le Morne peninsula
  [-0.59, 0.61],
  [-0.54, 0.41],  // Black River
  [-0.62, 0.17],  // Flic-en-Flac
  [-0.58, -0.11],
  [-0.50, -0.35], // Port Louis
  [-0.42, -0.56],
  [-0.30, -0.76], // north-west
  [-0.14, -0.92],
]

/**
 * A depth isoline: the island outline pushed outward and softened, so
 * successive rings lose the coastline's detail the way real bathymetry does as
 * it drops off the reef shelf.
 *
 * @param spread  0 = coastline, 1..n = progressively deeper contours
 */
export function isoline(spread: number): Array<[number, number]> {
  const grow = 1 + spread * 0.42
  // Deeper rings round off toward a circle.
  const round = Math.min(0.85, spread * 0.18)
  return ISLAND.map(([x, y], i) => {
    const ang = (i / ISLAND.length) * Math.PI * 2
    const circleX = Math.sin(ang)
    const circleY = -Math.cos(ang)
    const bx = x + (circleX - x) * round
    const by = y + (circleY - y) * round
    // Gentle deterministic irregularity so rings are not machine-perfect.
    const wobble = 1 + Math.sin(i * 2.4 + spread * 1.7) * 0.022
    return [bx * grow * wobble, by * grow * wobble] as [number, number]
  })
}

/**
 * Smooth closed path through the points, quadratic through edge midpoints.
 * This preserves the silhouette; an earlier bezier-with-midpoint-controls
 * version rounded Mauritius into a featureless ellipse.
 */
export function tracePath(
  ctx: CanvasRenderingContext2D,
  pts: Array<[number, number]>,
  cx: number, cy: number, scale: number,
  portion = 1,
) {
  const n = pts.length
  const P = (i: number): [number, number] => {
    const [x, y] = pts[((i % n) + n) % n]
    return [cx + x * scale, cy + y * scale]
  }
  const midOf = (a: [number, number], b: [number, number]): [number, number] =>
    [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]

  const steps = Math.max(1, Math.round(n * Math.min(1, Math.max(0, portion))))
  const start = midOf(P(-1), P(0))
  ctx.beginPath()
  ctx.moveTo(start[0], start[1])
  for (let i = 0; i < steps; i++) {
    const cur = P(i)
    const end = midOf(cur, P(i + 1))
    ctx.quadraticCurveTo(cur[0], cur[1], end[0], end[1])
  }
  if (portion >= 1) ctx.closePath()
}

/* ------------------------------------------------------------- soundings */

/**
 * Depth figures placed between contour rings, the way a chart marks them.
 * Radius is in isoline-spread units so they always land in the gaps, and the
 * set is fixed (not random) so the composition is identical every load —
 * a chart is a document, not a generative artwork.
 *
 * Twelve maximum, per the brief.
 */
export const SOUNDINGS: Array<{ depth: number; ring: number; angle: number }> = [
  { depth: 7,   ring: 0.55, angle: -1.9 },
  { depth: 12,  ring: 0.62, angle: 0.55 },
  { depth: 24,  ring: 1.45, angle: -0.65 },
  { depth: 42,  ring: 1.60, angle: 2.25 },
  { depth: 63,  ring: 2.40, angle: 1.15 },
  { depth: 88,  ring: 2.55, angle: -2.55 },
  { depth: 118, ring: 3.35, angle: 0.15 },
  { depth: 156, ring: 3.50, angle: 2.85 },
  { depth: 203, ring: 4.30, angle: -1.25 },
  { depth: 274, ring: 4.45, angle: 1.85 },
  { depth: 340, ring: 5.25, angle: -0.25 },
  { depth: 512, ring: 5.40, angle: 2.55 },
]
