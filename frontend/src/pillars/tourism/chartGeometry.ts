/* Workstream 2 — geometry for the tourism site chart.
 *
 * Pure functions only: no canvas, no React, no colour. SiteChart.tsx owns
 * pixels and tokens; this file only answers "where does a lon/lat land inside
 * a w x h box".
 *
 * Every position — coastline and site marker alike — goes through the SAME
 * projection, lonLatToWorld() from components/onboarding/terrain.ts. That is
 * deliberate: two projections would let the markers drift off the coast they
 * are plotted against, which is the one thing a map must not do.
 */
import { COASTLINE, lonLatToWorld } from '../../components/onboarding/terrain'

/** Suitability band. Mirrors backend suitability.py `Rating`. */
export type Band = 'good' | 'fair' | 'poor' | 'unknown'

/**
 * Narrows a backend rating string to a band.
 *
 * Anything the API did not send — a missing rating, an unrecognised value —
 * lands on 'unknown' and is drawn as "not rated". It is never promoted to a
 * band the backend did not state.
 */
export function bandOf(rating: string | null | undefined): Band {
  return rating === 'good' || rating === 'fair' || rating === 'poor' ? rating : 'unknown'
}

/**
 * Kilometres per world unit, DERIVED rather than restated.
 *
 * terrain.ts normalises by NORM = 0.30 degrees of latitude per world unit, but
 * that constant is private to it. Measuring a known one-degree step through the
 * public projection means the scale bar cannot silently go wrong if terrain.ts
 * is ever re-normalised.
 */
const KM_PER_DEG_LAT = 111.32
export const KM_PER_WORLD_UNIT = (() => {
  const [, a] = lonLatToWorld(57.5, -20)
  const [, b] = lonLatToWorld(57.5, -21)
  return KM_PER_DEG_LAT / Math.abs(b - a)
})()

export interface Fit {
  /** Screen x of world x=0. */
  cx: number
  /** Screen y of world y=0. */
  cy: number
  /** Pixels per world unit. Uniform on both axes. */
  scale: number
}

/**
 * Fits the coastline plus `extra` points into a w x h box.
 *
 * The scale is UNIFORM on both axes, so north stays up and two markers the
 * same distance apart on screen really are the same distance apart at sea.
 * A per-axis stretch would fit the box more tightly and lie about geography.
 */
export function fitWorld(
  extra: Array<[number, number]>, w: number, h: number, pad: number,
): Fit {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  const consider = ([x, y]: [number, number]) => {
    if (x < minX) minX = x
    if (x > maxX) maxX = x
    if (y < minY) minY = y
    if (y > maxY) maxY = y
  }
  COASTLINE.forEach(consider)
  extra.forEach(consider)

  const spanX = Math.max(1e-6, maxX - minX)
  const spanY = Math.max(1e-6, maxY - minY)
  const scale = Math.min(
    Math.max(1, w - pad * 2) / spanX,
    Math.max(1, h - pad * 2) / spanY,
  )
  return {
    scale,
    cx: w / 2 - ((minX + maxX) / 2) * scale,
    cy: h / 2 - ((minY + maxY) / 2) * scale,
  }
}

/** Projects one world point to screen space under a fit. */
export const toScreen = (fit: Fit, wx: number, wy: number): { x: number; y: number } =>
  ({ x: fit.cx + wx * fit.scale, y: fit.cy + wy * fit.scale })

/**
 * Largest "round" distance that still fits the space available to the scale
 * bar. A chart scale reading 13.7 km would be arithmetically correct and
 * useless; these are the steps a paper chart would print.
 */
export function niceScaleKm(maxKm: number): number {
  const steps = [1, 2, 5, 10, 20, 50, 100]
  let best = steps[0]
  for (const s of steps) if (s <= maxKm) best = s
  return best
}
