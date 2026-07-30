/* Workstream 2 — procedural site chart for the Sustainable Ocean Tourism pillar.
 *
 * A flat, north-up Canvas-2D chart of Mauritius with every catalogue site drawn
 * at its TRUE published lon/lat, through the same projection the onboarding
 * scene uses (terrain.ts → lonLatToWorld). No tiles, no images, no fetches: the
 * coastline is 71 traced degree pairs already in the bundle, so this renders
 * with the device in airplane mode, which is the state this app is built for.
 *
 * WHAT IS DRAWN, AND WHY NOTHING MORE
 *   coastline  real, traced from named coastal points (terrain.ts)
 *   markers    real, at the coordinates /sites publishes
 *   scale bar  derived from the projection, so it cannot drift
 * terrain.ts also exposes procedural depth rings. They are NOT drawn here. In
 * the onboarding scene they are ambient texture; beside true-position markers
 * they would read as a surveyed reef line, and this project has no bathymetry.
 * Honesty rule 4 — never invent data you do not have.
 *
 * ACCESSIBILITY
 *   The canvas is aria-hidden decoration and is NOT focusable. Clicking a
 *   marker is a pointer-only shortcut for something the real control does:
 *   the button list rendered alongside it in TourismSurface. Nothing here is
 *   the only route to anything.
 *
 * FLOORS (mirrors BathymetricScene)
 *   - Sunlight theme renders NO canvas at all.
 *   - prefers-reduced-motion / the a11y panel render ONE static frame: no entry
 *     stroke-on, no hover repaint.
 *   - Colour is never the only signal: band is shape AND colour AND the text
 *     label in the button list.
 */
import { useEffect, useMemo, useRef } from 'react'
import {
  mix, readToken, rgba, tracePath, type RGB,
} from '../../components/onboarding/chart'
import { COASTLINE, lonLatToWorld } from '../../components/onboarding/terrain'
import { useTheme } from '../../theme'
import {
  KM_PER_WORLD_UNIT, fitWorld, niceScaleKm, toScreen, type Band, type Fit,
} from './chartGeometry'

export interface ChartSite {
  site_id: string
  name: string
  latitude: number
  longitude: number
  protected_area: boolean
  band: Band
  /** 1-based ranking position, or null when no activity ranking exists. */
  rank: number | null
}

interface Props {
  sites: ChartSite[]
  selectedId: string | null
  onSelect: (siteId: string) => void
}

const ENTRY_MS = 800
/** Breathing room for the north arrow, scale bar and label chips. */
const pad = (w: number) => Math.max(16, Math.min(28, w * 0.06))
/** Below this canvas width, rank chips are dropped — they only collide. */
const LABEL_MIN_W = 300

const clamp01 = (v: number) => Math.min(1, Math.max(0, v))
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)

/**
 * Marker outline for a band. SHAPE is the primary signal — the same chart read
 * in greyscale, or by someone who cannot separate red from green, still sorts
 * the sites correctly.
 */
function markerPath(
  ctx: CanvasRenderingContext2D, band: Band, x: number, y: number, r: number,
) {
  ctx.beginPath()
  if (band === 'fair') {
    // square
    ctx.rect(x - r * 0.86, y - r * 0.86, r * 1.72, r * 1.72)
  } else if (band === 'poor') {
    // triangle, apex down
    ctx.moveTo(x, y + r * 1.15)
    ctx.lineTo(x + r * 1.08, y - r * 0.72)
    ctx.lineTo(x - r * 1.08, y - r * 0.72)
    ctx.closePath()
  } else {
    // circle — filled for 'good', hollow with a bar for 'unknown'
    ctx.arc(x, y, r, 0, Math.PI * 2)
  }
}

/** roundRect by hand: ctx.roundRect is not old enough to rely on. */
function roundRect(
  ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number,
) {
  const k = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + k, y)
  ctx.arcTo(x + w, y, x + w, y + h, k)
  ctx.arcTo(x + w, y + h, x, y + h, k)
  ctx.arcTo(x, y + h, x, y, k)
  ctx.arcTo(x, y, x + w, y, k)
  ctx.closePath()
}

export default function SiteChart({ sites, selectedId, onSelect }: Props) {
  const { theme, reduceMotion } = useTheme()
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  // Kept in a ref so a new onSelect identity does not tear down the canvas.
  const selectRef = useRef(onSelect)
  selectRef.current = onSelect
  // The entry animation plays once per MOUNT, not once per selection — a chart
  // that re-draws itself every time you pick a site is a distraction.
  const playedRef = useRef(false)

  /* The draw effect closes over `sites` from the render that created it, so it
   * must re-run whenever anything it paints changes. This signature is that
   * change set. Coordinates are fixed per site_id, so they need no entry. */
  const sig = useMemo(
    () => sites.map((s) => `${s.site_id}/${s.band}/${s.rank ?? ''}/${s.protected_area}`).join('|'),
    [sites],
  )

  // Declared BEFORE the draw effect so it runs first on mount, and on
  // StrictMode's remount, re-arming the entry animation exactly once.
  useEffect(() => {
    playedRef.current = false
    return () => { playedRef.current = false }
  }, [])

  useEffect(() => {
    // Sunlight renders no canvas: flat, maximum-contrast, illustration off.
    if (theme === 'sunlight') return
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!wrap || !canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    /* ------------------------------------------------------------- palette
     * No colour literal appears below. Every value is read from a semantic
     * token at runtime, so the themes drive the chart and nothing can drift
     * out of sync with styles/tokens.css. */
    const sea = mix(readToken('--surface'), readToken('--accent'), 0.07)
    const land = readToken('--surface-sunken')
    const edge = readToken('--border-strong')
    const hairline = readToken('--border')
    const ink = readToken('--text')
    const inkMuted = readToken('--text-muted')
    const accent = readToken('--accent')
    const bandInk: Record<Band, RGB> = {
      good: readToken('--success'),
      fair: readToken('--warning'),
      poor: readToken('--danger'),
      unknown: inkMuted,
    }
    const mono = getComputedStyle(document.documentElement)
      .getPropertyValue('--font-data').trim() || 'monospace'

    const placed = sites.map((s) => ({ site: s, w: lonLatToWorld(s.longitude, s.latitude) }))

    let w = 0, h = 0
    let fit: Fit = { cx: 0, cy: 0, scale: 1 }
    let hits: Array<{ id: string; x: number; y: number; r: number }> = []
    let hoverId: string | null = null
    // One static frame under reduced motion, and after the entry has played
    // once for this mount — re-selecting a site must not replay it.
    const still = reduceMotion || playedRef.current
    let progress = still ? 1 : 0

    const measure = () => {
      const rect = wrap.getBoundingClientRect()
      w = Math.max(1, Math.round(rect.width))
      h = Math.max(1, Math.round(rect.height))
      // Capped at 2 so a hi-dpi phone does not render four times the area.
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.round(w * dpr)
      canvas.height = Math.round(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      fit = fitWorld(placed.map((p) => p.w), w, h, pad(w))
    }

    /* Deliberately small. Three of the eight sites — Trou aux Biches, Grand
     * Baie and Pereybère — sit within ~2 km of each other on the north coast,
     * so at any scale that fits the island in a card their markers touch. The
     * honest answer is a small symbol with a cut ring around it (below), not a
     * displaced one: a marker that has been nudged apart is no longer at the
     * coordinate the API published. */
    const radius = () => Math.max(4.5, Math.min(7, w / 68))
    const fontSize = () => Math.max(11, Math.min(13, w / 34))

    /* --------------------------------------------------------- chart furniture */

    const drawNorth = () => {
      const x = pad(w) + 6, y = pad(w) - 2
      ctx.strokeStyle = rgba(inkMuted, 1)
      ctx.fillStyle = rgba(inkMuted, 1)
      ctx.lineWidth = 1.4
      ctx.globalAlpha = 0.9
      ctx.beginPath()
      ctx.moveTo(x, y + 20)
      ctx.lineTo(x, y + 4)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(x, y)
      ctx.lineTo(x + 4, y + 7)
      ctx.lineTo(x - 4, y + 7)
      ctx.closePath()
      ctx.fill()
      ctx.font = `600 11px ${mono}`
      ctx.textAlign = 'center'
      ctx.fillText('N', x, y + 33)
      ctx.globalAlpha = 1
    }

    const drawScaleBar = () => {
      const maxPx = Math.min(120, w * 0.34)
      const km = niceScaleKm((maxPx / fit.scale) * KM_PER_WORLD_UNIT)
      const px = (km / KM_PER_WORLD_UNIT) * fit.scale
      const x1 = w - pad(w), x0 = x1 - px, y = h - pad(w) - 6
      ctx.strokeStyle = rgba(inkMuted, 1)
      ctx.fillStyle = rgba(inkMuted, 1)
      ctx.lineWidth = 1.4
      ctx.globalAlpha = 0.9
      ctx.beginPath()
      ctx.moveTo(x0, y - 4)
      ctx.lineTo(x0, y)
      ctx.lineTo(x1, y)
      ctx.lineTo(x1, y - 4)
      ctx.stroke()
      ctx.font = `600 11px ${mono}`
      ctx.textAlign = 'right'
      ctx.fillText(`${km} km`, x1, y + 14)
      ctx.globalAlpha = 1
      ctx.textAlign = 'center'
    }

    /* ------------------------------------------------------------- labels
     * Unselected sites get their RANK NUMERAL, not their name. Eight name
     * chips do not fit beside an island that fills the frame — the first
     * version of this placed three of eight and silently dropped the rest,
     * which is worse than a legend. A numeral is ~16px, places nearly always,
     * and the button list right next to the chart is the key that reads it.
     * The selected site gets its full name, because there is only ever one.
     *
     * Placement searches outward from the island centre first, then rotates
     * off that radial, and SKIPS rather than overlapping. */
    let boxes: Array<[number, number, number, number]> = []
    const roomFor = (cx: number, cy: number, bw: number, bh: number) => {
      if (cx - bw / 2 < 2 || cx + bw / 2 > w - 2 || cy - bh / 2 < 2 || cy + bh / 2 > h - 2) return false
      for (const [ox, oy, ow, oh] of boxes) {
        if (Math.abs(cx - ox) < (bw + ow) / 2 + 4 && Math.abs(cy - oy) < (bh + oh) / 2 + 4) return false
      }
      return true
    }

    const drawLabel = (sx: number, sy: number, text: string, selected: boolean, alpha: number) => {
      const fs = selected ? fontSize() : Math.max(10, fontSize() - 1)
      ctx.font = `${selected ? 700 : 600} ${fs}px ${mono}`
      const bw = ctx.measureText(text).width + (selected ? 14 : 9)
      const bh = fs + (selected ? 10 : 7)
      const dx = sx - fit.cx, dy = sy - fit.cy
      const len = Math.max(1, Math.hypot(dx, dy))
      const ux = dx / len, uy = dy / len

      let cx = 0, cy = 0, ok = false
      const near = radius() + 3 + bh * 0.7
      search:
      for (const off of [near, near + bh * 0.9, near + bh * 1.9]) {
        for (const rot of [0, 0.55, -0.55, 1.1, -1.1, 1.75, -1.75]) {
          const c = Math.cos(rot), s = Math.sin(rot)
          cx = sx + (ux * c - uy * s) * off
          cy = sy + (ux * s + uy * c) * off
          if (roomFor(cx, cy, bw, bh)) { ok = true; break search }
        }
      }
      if (!ok) return false
      boxes.push([cx, cy, bw, bh])

      // Leader follows the chip's ACTUAL direction, which may be rotated off
      // the radial by the search above.
      const lx = cx - sx, ly = cy - sy
      const llen = Math.max(1, Math.hypot(lx, ly))
      ctx.globalAlpha = alpha
      ctx.strokeStyle = rgba(hairline, 1)
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(sx + (lx / llen) * (radius() + 2), sy + (ly / llen) * (radius() + 2))
      ctx.lineTo(cx - (lx / llen) * (bh / 2), cy - (ly / llen) * (bh / 2))
      ctx.stroke()

      roundRect(ctx, cx - bw / 2, cy - bh / 2, bw, bh, 4)
      ctx.fillStyle = rgba(sea, 1)
      ctx.fill()
      ctx.strokeStyle = rgba(selected ? accent : hairline, 1)
      ctx.lineWidth = selected ? 2 : 1
      ctx.stroke()

      ctx.fillStyle = rgba(ink, 1)
      ctx.textAlign = 'center'
      ctx.fillText(text, cx, cy + fs * 0.36)
      ctx.globalAlpha = 1
      return true
    }

    /* -------------------------------------------------------------- markers */

    const drawMarker = (
      p: { site: ChartSite; w: [number, number] }, sx: number, sy: number,
      selected: boolean, hovered: boolean, alpha: number,
    ) => {
      const base = radius()
      const r = selected ? base * 1.45 : base
      const colour = bandInk[p.site.band]
      ctx.globalAlpha = alpha

      // Selection ring first, under the glyph.
      if (selected || hovered) {
        ctx.beginPath()
        ctx.arc(sx, sy, r + (selected ? 7 : 5), 0, Math.PI * 2)
        ctx.strokeStyle = rgba(accent, 1)
        ctx.lineWidth = selected ? 2.5 : 1.5
        ctx.stroke()
      }

      // Marine protected area: a dashed collar. An echo of the note in the
      // list and the brief card — never the only place it is said.
      if (p.site.protected_area) {
        ctx.save()
        ctx.setLineDash([3, 3])
        ctx.beginPath()
        ctx.arc(sx, sy, r + 3.5, 0, Math.PI * 2)
        ctx.strokeStyle = rgba(ink, 1)
        ctx.globalAlpha = alpha * 0.75
        ctx.lineWidth = 1.2
        ctx.stroke()
        ctx.restore()
        ctx.globalAlpha = alpha
      }

      // Cut ring: the symbol is knocked out of whatever is behind it, so two
      // markers that overlap still read as two markers rather than one blob.
      markerPath(ctx, p.site.band, sx, sy, r)
      ctx.strokeStyle = rgba(sea, 1)
      ctx.lineWidth = 3.2
      ctx.stroke()

      markerPath(ctx, p.site.band, sx, sy, r)
      if (p.site.band === 'unknown') {
        // Hollow, with a bar: reads as "no rating", not as a quiet good.
        ctx.fillStyle = rgba(sea, 1)
        ctx.fill()
        ctx.strokeStyle = rgba(colour, 1)
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(sx - r * 0.62, sy)
        ctx.lineTo(sx + r * 0.62, sy)
        ctx.stroke()
      } else {
        ctx.fillStyle = rgba(colour, 1)
        ctx.fill()
        ctx.strokeStyle = rgba(edge, 1)
        ctx.lineWidth = 1.4
        ctx.stroke()
      }
      ctx.globalAlpha = 1
    }

    /* ----------------------------------------------------------- whole frame */

    const frame = (progress: number) => {
      const p = easeOut(clamp01(progress))
      ctx.clearRect(0, 0, w, h)
      ctx.textBaseline = 'alphabetic'
      ctx.textAlign = 'center'

      ctx.fillStyle = rgba(sea, 1)
      ctx.fillRect(0, 0, w, h)

      // Land fills first, then the coastline strokes on over it.
      tracePath(ctx, COASTLINE, fit.cx, fit.cy, fit.scale, 1)
      ctx.globalAlpha = Math.min(1, p * 1.8)
      ctx.fillStyle = rgba(land, 1)
      ctx.fill()
      ctx.globalAlpha = 1

      tracePath(ctx, COASTLINE, fit.cx, fit.cy, fit.scale, p)
      ctx.strokeStyle = rgba(edge, 1)
      ctx.lineWidth = 1.5
      ctx.stroke()

      drawNorth()
      drawScaleBar()

      hits = []
      boxes = []
      const withScreen = placed.map((entry) => {
        const s = toScreen(fit, entry.w[0], entry.w[1])
        return { entry, sx: s.x, sy: s.y }
      })

      // Markers, unselected first so the selected one is never overdrawn.
      const order = [...withScreen].sort(
        (a, b) => Number(a.entry.site.site_id === selectedId) - Number(b.entry.site.site_id === selectedId),
      )
      order.forEach(({ entry, sx, sy }) => {
        const i = placed.indexOf(entry)
        const local = clamp01((p - 0.3 - i * 0.045) / 0.3)
        if (local <= 0) return
        hits.push({ id: entry.site.site_id, x: sx, y: sy, r: radius() + 8 })
        drawMarker(
          entry, sx, sy,
          entry.site.site_id === selectedId,
          entry.site.site_id === hoverId,
          local,
        )
      })

      // Labels last, so no marker paints over a name. The selected site is
      // placed FIRST and therefore always wins its space.
      const labelAlpha = clamp01((p - 0.6) / 0.35)
      if (labelAlpha > 0) {
        // Reserve every marker (and the selection ring) before placing chips,
        // so a chip can never land on top of a symbol it is not labelling.
        for (const { entry, sx, sy } of withScreen) {
          const rr = entry.site.site_id === selectedId
            ? radius() * 1.45 + 9
            : radius() + 2
          boxes.push([sx, sy, rr * 2, rr * 2])
        }
        const byPriority = [...withScreen].sort((a, b) => {
          const sa = a.entry.site.site_id === selectedId ? -1 : 0
          const sb = b.entry.site.site_id === selectedId ? -1 : 0
          if (sa !== sb) return sa - sb
          return (a.entry.site.rank ?? 99) - (b.entry.site.rank ?? 99)
        })
        for (const { entry, sx, sy } of byPriority) {
          const selected = entry.site.site_id === selectedId
          if (selected) {
            drawLabel(sx, sy, entry.site.rank ? `${entry.site.rank}. ${entry.site.name}` : entry.site.name,
              true, labelAlpha)
          } else if (w >= LABEL_MIN_W && entry.site.rank) {
            drawLabel(sx, sy, String(entry.site.rank), false, labelAlpha)
          }
        }
      }
    }

    /* -------------------------------------------------------------- pointer */

    const hitTest = (ev: MouseEvent): string | null => {
      const rect = canvas.getBoundingClientRect()
      const x = ev.clientX - rect.left, y = ev.clientY - rect.top
      let best: string | null = null
      let bestD = Infinity
      for (const hit of hits) {
        const d = Math.hypot(x - hit.x, y - hit.y)
        if (d <= hit.r && d < bestD) { best = hit.id; bestD = d }
      }
      return best
    }

    const onMove = (ev: MouseEvent) => {
      const id = hitTest(ev)
      canvas.style.cursor = id ? 'pointer' : 'default'
      if (id === hoverId) return
      hoverId = id
      // Reduced motion gets exactly one frame, so hover stays cursor-only.
      if (!reduceMotion) frame(progress)
    }
    const onLeave = () => {
      if (hoverId === null) return
      hoverId = null
      if (!reduceMotion) frame(progress)
    }
    const onClick = (ev: MouseEvent) => {
      const id = hitTest(ev)
      if (id) selectRef.current(id)
    }

    canvas.addEventListener('mousemove', onMove)
    canvas.addEventListener('mouseleave', onLeave)
    canvas.addEventListener('click', onClick)

    /* A resize must repaint at the CURRENT entry progress, not at 1.
     * ResizeObserver delivers its first callback after the initial rAF tick,
     * so redrawing at 1 there would finish the entry animation on frame one. */
    const ro = new ResizeObserver(() => {
      measure()
      frame(progress)
    })
    ro.observe(wrap)

    measure()
    frame(progress)

    let raf = 0
    if (!still) {
      const t0 = performance.now()
      const loop = (now: number) => {
        progress = (now - t0) / ENTRY_MS
        frame(progress)
        if (progress < 1) raf = requestAnimationFrame(loop)
        else { progress = 1; playedRef.current = true }
      }
      raf = requestAnimationFrame(loop)
    }

    return () => {
      if (raf) cancelAnimationFrame(raf)
      ro.disconnect()
      canvas.removeEventListener('mousemove', onMove)
      canvas.removeEventListener('mouseleave', onLeave)
      canvas.removeEventListener('click', onClick)
    }
    // `sites` is read through the closure; `sig` is the signature of everything
    // in it that this effect paints.
  }, [sig, selectedId, theme, reduceMotion])

  if (theme === 'sunlight') return null

  return (
    <div className="tou-chart" ref={wrapRef}>
      <canvas ref={canvasRef} className="tou-chart__canvas" aria-hidden="true" />
    </div>
  )
}
