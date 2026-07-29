/**
 * Bathymetric terrain: geometry, camera and the time-of-day palette.
 *
 * Theme: "Blue Economy — Mauritius and Beyond." The island is small; the ocean
 * territory around it is vast. The scene is built to say that.
 *
 * Everything is generated from the numbers in this file. No images, no fetches,
 * no fonts to download — it renders with the device in airplane mode.
 * No colour literal appears anywhere: every value is read from a CSS custom
 * property at runtime, so the themes drive the scene.
 *
 * ALL geometry here is precomputed ONCE at mount. The render loop only projects
 * and strokes; it never regenerates a point array.
 */
import { mix, readToken, type RGB } from './chart'

/* ===================================================================== camera */

export interface Camera {
  heading: number      // radians, rotation about Y
  pitch: number        // radians, rotation about X (negative looks down)
  dist: number         // world units from the origin
  height: number       // camera elevation above the Z=0 plane
  f: number            // focal length in px
  cx: number
  cy: number
}

export interface P2 { x: number; y: number; depth: number }

/**
 * World -> screen. Rotate about Y (heading), then X (pitch), then divide.
 * One function, no matrix library.
 *
 * `depth` comes back with the point so the caller can fade by distance — that
 * opacity ramp is what actually sells the 3D, more than the projection does.
 */
export function project(x: number, y: number, z: number, c: Camera): P2 {
  // heading
  const ch = Math.cos(c.heading), sh = Math.sin(c.heading)
  const rx = x * ch - y * sh
  const ry = x * sh + y * ch

  // The plane lies flat: world Y becomes ground-depth, world Z is elevation.
  const gz = ry + c.dist          // distance in front of the camera
  const gy = z - c.height         // height relative to the camera

  // pitch
  const cp = Math.cos(c.pitch), sp = Math.sin(c.pitch)
  const py = gy * cp - gz * sp
  const pz = gy * sp + gz * cp

  const denom = Math.max(0.06, pz)
  return { x: c.cx + (rx * c.f) / denom, y: c.cy + (py * c.f) / denom, depth: denom }
}

/* ========================================================= Mauritius coastline
 *
 * Traced in real degrees inside the brief's bounding box
 * (19.98S-20.53S, 57.30E-57.81E) through named coastal points, then normalised
 * so the island's mean radius is 1 world unit.
 *
 * Anticlockwise from Cap Malheureux (north).
 */
const COAST_DEG: Array<[number, number]> = [
  [57.614, -19.984], // Cap Malheureux (northern tip)
  [57.646, -19.997], // Grand Gaube
  [57.679, -20.028],
  [57.706, -20.093], // Roches Noires
  [57.739, -20.128], // Poste Lafayette
  [57.775, -20.176],
  [57.782, -20.205], // Belle Mare
  [57.796, -20.238], // Trou d'Eau Douce
  [57.788, -20.288],
  [57.771, -20.336],
  [57.752, -20.375],
  [57.731, -20.428], // Pointe d'Esny
  [57.717, -20.443], // Blue Bay
  [57.699, -20.428],
  [57.700, -20.407], // Mahebourg (Grand Port notch)
  [57.672, -20.418],
  [57.641, -20.451],
  [57.606, -20.484],
  [57.556, -20.507],
  [57.518, -20.517], // Souillac (south coast)
  [57.474, -20.510],
  [57.436, -20.503],
  [57.400, -20.494],
  [57.383, -20.499], // Baie du Cap
  [57.348, -20.487],
  [57.319, -20.470],
  [57.313, -20.457], // Le Morne Brabant (south-west)
  [57.327, -20.436],
  [57.343, -20.410],
  [57.355, -20.376],
  [57.366, -20.325], // Tamarin
  [57.363, -20.274], // Flic en Flac
  [57.372, -20.245],
  [57.386, -20.222],
  [57.410, -20.199],
  [57.448, -20.180],
  [57.478, -20.170],
  [57.498, -20.161], // Port Louis
  [57.512, -20.135],
  [57.520, -20.100],
  [57.526, -20.062], // Pointe aux Piments
  [57.545, -20.038],
  [57.566, -20.020],
  [57.580, -20.013], // Grand Baie
  [57.596, -19.996],
]

/** Named places, projected into the scene beside the island. */
export const PLACES: Array<{ name: string; lon: number; lat: number }> = [
  { name: 'Port Louis', lon: 57.498, lat: -20.161 },
  { name: 'Grand Baie', lon: 57.580, lat: -20.013 },
  { name: 'Mahebourg', lon: 57.700, lat: -20.407 },
  { name: 'Le Morne', lon: 57.313, lat: -20.457 },
  { name: "Trou d'Eau Douce", lon: 57.796, lat: -20.238 },
]

// Normalisation constants, derived once from the coastline.
const LON0 = 57.555, LAT0 = -20.25
// Degrees of longitude shrink with latitude; at 20S that is cos(20 deg).
const LON_SCALE = Math.cos((20.25 * Math.PI) / 180)
const NORM = 0.30   // -> island mean radius ~1 world unit

export function lonLatToWorld(lon: number, lat: number): [number, number] {
  return [((lon - LON0) * LON_SCALE) / NORM, -((lat - LAT0)) / NORM]
}

export const COASTLINE: Array<[number, number]> =
  COAST_DEG.map(([lon, lat]) => lonLatToWorld(lon, lat))

/* ====================================================== depth rings (isolines)
 *
 * Shallow rings hug the coastline; deep rings expand fast, round toward a
 * circle as the coastal detail drops away off the shelf, and run off frame.
 */
export interface Ring {
  depth: number          // metres, negative
  pts: Array<[number, number]>
  opacity: number
  weight: number
  label?: string
  /** Reef ring carries a real gap along the south coast near Souillac. */
  gap?: [number, number]
}

const RING_SPEC: Array<{ depth: number; scale: number; opacity: number; weight: number; label?: string }> = [
  { depth: 0,     scale: 1.00, opacity: 0.95, weight: 1.6 },
  { depth: -20,   scale: 1.13, opacity: 0.88, weight: 1.9 },
  { depth: -50,   scale: 1.38, opacity: 0.60, weight: 1.2, label: '-50m' },
  { depth: -100,  scale: 1.68, opacity: 0.48, weight: 1.1 },
  { depth: -200,  scale: 2.05, opacity: 0.38, weight: 1.0, label: '-200m' },
  { depth: -500,  scale: 2.60, opacity: 0.30, weight: 0.9 },
  { depth: -1000, scale: 3.30, opacity: 0.23, weight: 0.85, label: '-1000m' },
  { depth: -2000, scale: 4.20, opacity: 0.17, weight: 0.8 },
  { depth: -3000, scale: 5.20, opacity: 0.13, weight: 0.75 },
  { depth: -4000, scale: 6.30, opacity: 0.10, weight: 0.75, label: '-4000m' },
]

/** Resample a closed loop to exactly n points, by arc length. */
function resample(loop: Array<[number, number]>, n: number): Array<[number, number]> {
  const segLen: number[] = []
  let total = 0
  for (let i = 0; i < loop.length; i++) {
    const a = loop[i], b = loop[(i + 1) % loop.length]
    const d = Math.hypot(b[0] - a[0], b[1] - a[1])
    segLen.push(d); total += d
  }
  const out: Array<[number, number]> = []
  const step = total / n
  let seg = 0, acc = 0
  for (let i = 0; i < n; i++) {
    const target = i * step
    while (acc + segLen[seg] < target && seg < segLen.length - 1) { acc += segLen[seg]; seg++ }
    const t = segLen[seg] === 0 ? 0 : (target - acc) / segLen[seg]
    const a = loop[seg], b = loop[(seg + 1) % loop.length]
    out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
  }
  return out
}

const RING_POINTS = 64

/**
 * Builds every ring once. Deeper rings blend toward a circle, because past the
 * shelf break the coastline's shape stops mattering.
 */
export function buildRings(): Ring[] {
  const base = resample(COASTLINE, RING_POINTS)
  return RING_SPEC.map(({ depth, scale, opacity, weight, label }) => {
    const round = depth === 0 ? 0 : Math.min(0.9, Math.abs(depth) / 2600)
    const pts = base.map(([x, y], i) => {
      const ang = (i / RING_POINTS) * Math.PI * 2
      const cxp = Math.sin(ang), cyp = -Math.cos(ang)
      const bx = x + (cxp - x) * round
      const by = y + (cyp - y) * round
      return [bx * scale, by * scale] as [number, number]
    })
    return {
      depth, pts, opacity, weight, label,
      // The fringing reef is broken along the south coast near Souillac. Indices
      // are into the resampled loop, which starts at Cap Malheureux going east.
      gap: depth === -20 ? [30, 36] : undefined,
    }
  })
}

/** The EEZ: a vast faint ring far out on the deep plane. */
export const EEZ_SCALE = 15
export function buildEez(): Array<[number, number]> {
  const pts: Array<[number, number]> = []
  for (let i = 0; i < RING_POINTS; i++) {
    const a = (i / RING_POINTS) * Math.PI * 2
    // Slightly non-circular so it reads as a boundary, not a compass circle.
    const r = EEZ_SCALE * (1 + Math.sin(a * 2 + 0.6) * 0.06)
    pts.push([Math.sin(a) * r, -Math.cos(a) * r])
  }
  return pts
}

/** Drifting motes for depth perception. Deterministic, so the scene is stable. */
export interface Mote { x: number; y: number; z: number; phase: number }
export function buildMotes(n = 26): Mote[] {
  const out: Mote[] = []
  for (let i = 0; i < n; i++) {
    const a = i * 2.399963           // golden angle, even spread without clumping
    const r = 1.4 + ((i * 37) % 100) / 100 * 7.5
    out.push({
      x: Math.sin(a) * r,
      y: -Math.cos(a) * r,
      z: -0.15 - ((i * 61) % 100) / 100 * 0.85,
      phase: (i * 0.37) % (Math.PI * 2),
    })
  }
  return out
}

/* ================================================================== palette
 *
 * Paper and ink. Deep water IS the background; there is no sky and no horizon.
 * Ink brightens as depth decreases, so the island is the light focal point and
 * the abyss falls away into the paper. Two hues plus opacity ramps.
 */
export interface Palette { paper: RGB; ink: RGB; accent: RGB }

export function paletteForHour(hour: number): Palette {
  const abyss = readToken('--abyss')
  const lagoon = readToken('--lagoon')
  const lagoonSoft = readToken('--lagoon-soft')
  const foam = readToken('--foam')
  const coralSoft = readToken('--coral-soft')

  // Pre-dawn: abyss paper, cool cyan ink.
  if (hour < 6) return { paper: mix(abyss, { r: 0, g: 0, b: 0 }, 0.35), ink: lagoonSoft, accent: lagoon }
  // Dawn.
  if (hour < 9) return { paper: mix(abyss, lagoon, 0.18), ink: mix(lagoonSoft, coralSoft, 0.35), accent: coralSoft }
  // Day: deep lagoon paper, foam ink.
  if (hour < 16) return { paper: mix(abyss, lagoon, 0.42), ink: foam, accent: lagoonSoft }
  // Dusk: warm coral-tinted ink.
  if (hour < 19) return { paper: mix(abyss, lagoon, 0.22), ink: mix(foam, coralSoft, 0.5), accent: coralSoft }
  // Night: near-black paper, dim lagoon ink.
  return { paper: mix(abyss, { r: 0, g: 0, b: 0 }, 0.55), ink: mix(lagoon, foam, 0.25), accent: lagoon }
}
