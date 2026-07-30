/* Port Louis approach chart — canvas 2D, STATIC.
 *
 * Draws the real Mauritius coastline (components/onboarding/terrain.ts, traced
 * in real degrees) with true-scale range rings around Port Louis, and each
 * expected arrival plotted at its TRUE distance from the port.
 *
 * THE HONESTY CONSTRAINT THAT SHAPED THIS DESIGN: the AIS payload exposes
 * `distance_nm` per vessel but no bearing (see transport/types.ts). A scatter
 * of vessels around the rings would therefore be an invention. Instead every
 * vessel sits on ONE schematic approach line heading out to open sea — ranges
 * true, direction explicitly labelled as not reported (legend lives in
 * TransportSurface as real HTML text, translatable and screen-readable).
 *
 * Static by design: no rAF loop, no animation — the canvas redraws only on
 * data / theme / resize. That satisfies reduced-motion by construction and
 * costs zero battery. aria-hidden: every figure drawn here is also in the
 * arrivals table, so the canvas is decoration, not the record.
 *
 * Sunlight renders no canvas at all (same rule as every other chart surface).
 */
import { useEffect, useRef } from 'react'
import { useTheme } from '../../theme'
import { COASTLINE, lonLatToWorld } from '../../components/onboarding/terrain'
import type { ArrivalsBrief } from './types'

/** World units per nautical mile, derived from the projection itself (1 nm =
 *  1/60 degree of latitude) rather than duplicating terrain.ts constants. */
const WORLD_PER_NM = (() => {
  const [, y1] = lonLatToWorld(57.5, -20.15)
  const [, y2] = lonLatToWorld(57.5, -20.15 + 1 / 60)
  return Math.abs(y2 - y1)
})()

/**
 * Screen direction of the schematic approach line: NW of Port Louis, i.e. up
 * and to the left.
 *
 * This has to be open water for the whole 15 nm, or vessels get drawn sitting
 * on land. Port Louis is on the island's north-west coast and Mauritius extends
 * south and east from there, so NW is the only heading that clears the
 * coastline — a WSW ray (tried first) ran roughly PARALLEL to the west coast
 * and put the further arrivals on the beach.
 */
const RAY = (() => {
  const x = -0.92, y = -0.39
  const len = Math.hypot(x, y)
  return { x: x / len, y: y / len }
})()

const read = (name: string, fallback: string) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

export default function ApproachChart({ brief }: { brief: ArrivalsBrief }) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { theme } = useTheme()

  useEffect(() => {
    if (theme === 'sunlight') return
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!wrap || !canvas) return

    const draw = () => {
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = wrap.clientWidth
      // Taller than a typical banner on purpose: the vertical extent is what
      // sets pixels-per-nautical-mile, and at 360px the arrivals (2-11 nm)
      // bunched into ~90px with their labels on top of each other.
      const h = Math.max(280, Math.min(440, Math.round(w * 0.62)))
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      // Semantic tokens only — resolved at draw time so themes repaint free.
      const water = read('--surface-sunken', '#DCE8EA')
      const land = read('--bg-alt', '#F5EFE6')
      const coast = read('--border-strong', '#5F7B82')
      const hair = read('--border', '#C9D8DB')
      const ink = read('--text', '#0A2540')
      const muted = read('--text-muted', '#4C6076')
      const accent = read('--accent', '#0E7C86')
      const mono = read('--font-data', 'monospace')

      const { port, congestion, expected_arrivals: arrivals } = brief

      // Ring extent: everything real must fit — the approach radius and the
      // farthest listed vessel — rounded up to the next 5 nm ring.
      const maxVessel = arrivals.reduce((m, a) => Math.max(m, a.distance_nm), 0)
      const maxRange = Math.max(15, Math.ceil(Math.max(congestion.approach_radius_nm, maxVessel) / 5) * 5)

      // Port slightly left of centre and mid-height: the island fills the space
      // down-and-right of it (Mauritius lies SE of Port Louis) while the NW
      // approach ray runs up-and-left. Putting the port right-of-centre clipped
      // the island off the right edge and wasted the whole left half on water.
      const px = w * 0.46
      const py = h * 0.46
      const pad = 26
      // Scale so the outermost ring fits every direction the ray or rings need.
      const pxPerNm = Math.min(px - pad, py - pad, h - py - pad) / maxRange
      const pxPerWorld = pxPerNm / WORLD_PER_NM

      const [pwx, pwy] = lonLatToWorld(port.longitude, port.latitude)
      const toScreen = (wx: number, wy: number): [number, number] =>
        [px + (wx - pwx) * pxPerWorld, py + (wy - pwy) * pxPerWorld]

      // -- water, then the real coastline --------------------------------
      ctx.fillStyle = water
      ctx.fillRect(0, 0, w, h)

      ctx.beginPath()
      COASTLINE.forEach(([x, y], i) => {
        const [sx, sy] = toScreen(x, y)
        if (i === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy)
      })
      ctx.closePath()
      ctx.fillStyle = land
      ctx.fill()
      ctx.strokeStyle = coast
      ctx.lineWidth = 1.5
      ctx.stroke()

      // -- range rings, 5 nm steps; approach radius gets the accent -------
      ctx.font = `10px ${mono}`
      ctx.textAlign = 'center'
      for (let r = 5; r <= maxRange; r += 5) {
        const rp = r * pxPerNm
        const isApproach = Math.abs(r - congestion.approach_radius_nm) < 2.5
        ctx.beginPath()
        ctx.arc(px, py, rp, 0, Math.PI * 2)
        ctx.setLineDash(isApproach ? [] : [3, 5])
        ctx.strokeStyle = isApproach ? accent : hair
        ctx.lineWidth = isApproach ? 1.5 : 1
        ctx.stroke()
        ctx.setLineDash([])
        ctx.fillStyle = muted
        ctx.fillText(`${r} nm`, px, py - rp - 4)
      }

      // -- the schematic approach line ------------------------------------
      const rayEnd = maxRange * pxPerNm
      ctx.beginPath()
      ctx.moveTo(px, py)
      ctx.lineTo(px + RAY.x * rayEnd, py + RAY.y * rayEnd)
      ctx.setLineDash([1, 5])
      ctx.strokeStyle = muted
      ctx.lineWidth = 1
      ctx.stroke()
      ctx.setLineDash([])

      // -- port marker ------------------------------------------------------
      ctx.beginPath()
      ctx.arc(px, py, 4, 0, Math.PI * 2)
      ctx.fillStyle = accent
      ctx.fill()
      ctx.font = `600 11px ${mono}`
      ctx.fillStyle = ink
      ctx.textAlign = 'left'
      ctx.fillText(port.name.toUpperCase(), px + 9, py + 4)

      // -- vessels at TRUE range along the line ---------------------------
      //
      // NO VESSEL NAMES ON THE CANVAS. Five arrivals inside 11 nm sit within
      // ~120px of each other on the approach line, and their names collided
      // into an unreadable smear at every width tested — including 1920px.
      // The canvas answers one question ("how far out is the traffic, relative
      // to the port and the island") and the table immediately below answers
      // "which vessel". Short range figures alternate above and below the line
      // so the spatial claim stays legible; identity lives in the table, which
      // is also the accessible copy since this canvas is aria-hidden.
      const sorted = [...arrivals].sort((a, b) => a.distance_nm - b.distance_nm)
      ctx.font = `10px ${mono}`
      sorted.forEach((v, i) => {
        const d = v.distance_nm * pxPerNm
        const vx = px + RAY.x * d
        const vy = py + RAY.y * d

        // Hull: unfilled triangle pointing back toward the port (inbound),
        // same hairline chart language as the rest of the app's vessels.
        const ux = -RAY.x, uy = -RAY.y      // direction of travel
        const nx = -uy, ny = ux
        ctx.beginPath()
        ctx.moveTo(vx + ux * 6, vy + uy * 6)
        ctx.lineTo(vx - ux * 4 + nx * 3.5, vy - uy * 4 + ny * 3.5)
        ctx.lineTo(vx - ux * 4 - nx * 3.5, vy - uy * 4 - ny * 3.5)
        ctx.closePath()
        ctx.strokeStyle = ink
        ctx.lineWidth = 1.2
        ctx.stroke()

        const above = i % 2 === 0
        ctx.fillStyle = muted
        ctx.textAlign = 'center'
        ctx.fillText(v.distance_nm.toFixed(1), vx, above ? vy - 11 : vy + 19)
      })
    }

    draw()
    const ro = new ResizeObserver(draw)
    ro.observe(wrap)
    return () => ro.disconnect()
  }, [brief, theme])

  // Sunlight: no canvas anywhere in the app — the table below carries every
  // figure, so nothing is lost, and glare gets no soft edges to wash out.
  if (theme === 'sunlight') return null

  return (
    <div ref={wrapRef} className="tpt-chart">
      <canvas ref={canvasRef} aria-hidden="true" />
    </div>
  )
}
