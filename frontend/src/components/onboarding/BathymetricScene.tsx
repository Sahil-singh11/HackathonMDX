/**
 * "Blue Economy — Mauritius and Beyond."
 *
 * A pseudo-3D wireframe seafloor built from stacked depth contours, viewed from
 * inside the seascape rather than above a map. The island is small; the EEZ
 * ring is vast and runs past the frame. That contrast is the whole point.
 *
 * The 3D read comes from three things, none of which need a shader:
 *   1. the depth-fade opacity ramp (far rings faint, shallow rings crisp)
 *   2. a specular highlight that tracks the cursor across the shallow contours
 *   3. motes at varying Z that parallax against the camera
 *
 * Performance contract:
 *   - ALL geometry precomputed once at mount; the loop only projects and strokes
 *   - one requestAnimationFrame loop, capped at 30fps, paused when tab hidden
 *   - ~780 points total, against a 2,000 budget
 *   - devicePixelRatio capped at 2 so a projector does not render 4x area
 *
 * Floors:
 *   - prefers-reduced-motion renders ONE composed static frame at a chosen
 *     angle, with no drift, no reactivity and no pulse
 *   - Sunlight theme renders nothing; the page falls back to flat white
 *   - aria-hidden, pointer-events:none — carries no information, controls nothing
 */
import { useEffect, useRef } from 'react'
import { useTheme } from '../../theme'
import { inkForSky, luminance, rgba } from './chart'
import {
  PLACES, buildMotes, buildRings, lonLatToWorld,
  paletteForHour, project, type Camera, type Ring,
} from './terrain'

const FRAME_MS = 1000 / 30
const ENTRY_MS = 1200
const PULSE_PERIOD = 8000

// Camera constants (see the plan table).
// 62 degrees: steep enough that the coastline reads as Mauritius, shallow
// enough that the stacked contours still recede. A full 90 would flatten them
// into concentric rings and kill the depth entirely.
const BASE_PITCH = -62 * Math.PI / 180
const ENTRY_PITCH = -48 * Math.PI / 180
// The island has radius 1. Sitting far back is what makes it read as SMALL
// against a vast zone - the whole point of the theme. At the previous 1.55 the
// island filled half the frame, saying the opposite.
const BASE_DIST = 2.5
const ENTRY_DIST = 1.2
const BASE_HEIGHT = 5.5
const ENTRY_HEIGHT = 2.6
// Near-plane cull. Points closer than this project to enormous coordinates and
// knot the deep rings where they pass behind the viewer.
const NEAR = 0.5
// Longer lens = weaker perspective, so near contours do not balloon.
const FOV = 38 * Math.PI / 180
const ORBIT_HEADING = 8 * Math.PI / 180   // max mouse influence
const ORBIT_PITCH = 5 * Math.PI / 180
const LERP = 0.05
const IDLE_DRIFT = 0.02 * Math.PI / 180   // per frame

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)

export function BathymetricScene() {
  const ref = useRef<HTMLCanvasElement>(null)
  const { theme, reduceMotion } = useTheme()

  useEffect(() => {
    if (theme === 'sunlight') return
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    /* ---------------------------------------- geometry: built ONCE, never in the loop */
    const rings = buildRings()
    const motes = buildMotes()
    const places = PLACES.map((p) => ({ ...p, w: lonLatToWorld(p.lon, p.lat) }))

    const hour = new Date().getHours() + new Date().getMinutes() / 60
    const pal = paletteForHour(hour)
    const monoFont = getComputedStyle(document.documentElement)
      .getPropertyValue('--font-data').trim() || 'monospace'

    // The masthead sits directly on the painted paper, whose colour is driven by
    // the CLOCK while --text is driven by the THEME. They disagree: in Day at
    // night-time hours the paper is near-black and --text is navy, which measured
    // 1.22:1. Pick whichever semantic ink actually wins against the paper.
    document.documentElement.style.setProperty('--onboard-ink', rgba(inkForSky(pal.paper), 1))

    // The CARD has the same problem the masthead had: its surface follows the
    // THEME while the paper behind it follows the CLOCK. In Day at night-time
    // hours that produced a bright cream slab against a near-black scene -
    // visually loud, and bad for night vision. Publish what the scene actually
    // is, and let CSS pick the panel treatment from tokens.
    document.documentElement.setAttribute(
      'data-scene', luminance(pal.paper) < 0.18 ? 'dark' : 'light')

    let w = 0, h = 0, dpr = 1
    const cam: Camera = {
      heading: 0, pitch: BASE_PITCH, dist: BASE_DIST, height: BASE_HEIGHT,
      f: 800, cx: 0, cy: 0,
    }

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = window.innerWidth
      h = window.innerHeight
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      cam.f = (h / 2) / Math.tan(FOV / 2)
      // Island right of centre on wide screens so the card takes the left and
      // the deep contours cascade across the rest of the frame.
      cam.cx = w >= 900 ? w * 0.62 : w * 0.5
      cam.cy = 0
    }

    /**
     * Re-centre so the island lands at a fixed point in frame regardless of
     * pitch, distance or the entry dolly. Without this, changing the camera
     * pushed the island off-screen and the composition fell apart.
     */
    const recentre = () => {
      cam.cy = 0
      const o = project(0, 0, 0, cam)
      // Island high in the frame so the deep rings sweep past the bottom edge.
      cam.cy = (w >= 900 ? h * 0.48 : h * 0.30) - o.y
    }
    resize()

    /* ------------------------------------------------------------- reactivity */
    let targetH = 0, targetP = 0     // mouse-driven offsets
    let curH = 0, curP = 0
    let lightX = 0.5, lightY = 0.35  // normalised cursor, drives the specular
    let drift = 0

    const onPointer = (px: number, py: number) => {
      const nx = (px / w) * 2 - 1
      const ny = (py / h) * 2 - 1
      targetH = nx * ORBIT_HEADING
      targetP = -ny * ORBIT_PITCH
      lightX = px / w
      lightY = py / h
    }
    const onMouse = (e: MouseEvent) => onPointer(e.clientX, e.clientY)
    const onTouch = (e: TouchEvent) => {
      const t = e.touches[0]
      if (t) onPointer(t.clientX, t.clientY)
    }
    // Gyroscope ONLY if permission is already granted; never prompt.
    const onOrient = (e: DeviceOrientationEvent) => {
      if (e.gamma == null || e.beta == null) return
      targetH = Math.max(-1, Math.min(1, e.gamma / 45)) * ORBIT_HEADING
      targetP = Math.max(-1, Math.min(1, (e.beta - 45) / 45)) * ORBIT_PITCH
    }

    /* ------------------------------------------------------------- drawing */

    /** Strokes a projected loop, skipping an index range for the reef gap. */
    const strokeLoop = (
      pts: Array<[number, number]>, z: number, alpha: number, weight: number,
      gap?: [number, number], portion = 1,
    ) => {
      const n = pts.length
      const count = Math.max(2, Math.round(n * portion))
      ctx.beginPath()
      let drawing = false
      for (let i = 0; i <= count; i++) {
        const idx = i % n
        if (gap && idx >= gap[0] && idx <= gap[1]) { drawing = false; continue }
        const [x, y] = pts[idx]
        const p = project(x, y, z, cam)
        // Cull points that fall behind the camera.
        if (p.depth <= NEAR) { drawing = false; continue }
        if (!drawing) { ctx.moveTo(p.x, p.y); drawing = true } else { ctx.lineTo(p.x, p.y) }
      }
      ctx.globalAlpha = alpha
      ctx.lineWidth = weight
      ctx.stroke()
      ctx.globalAlpha = 1
    }

    const drawRing = (r: Ring, t: number, entry: number, ringIndex: number) => {
      // Contours stroke on shallow -> deep during entry.
      const start = ringIndex * 0.06
      const local = Math.min(1, Math.max(0, (entry - start) / 0.30))
      if (local <= 0) return

      // World Z for the ring: compressed so 4000m does not dwarf the scene.
      const z = r.depth === 0 ? 0 : -Math.pow(Math.abs(r.depth), 0.42) * 0.055

      // Sonar pulse travels DOWN through the rings, shallow to deep.
      const pulse = (t % PULSE_PERIOD) / PULSE_PERIOD
      const near = Math.abs(pulse * rings.length * 1.2 - ringIndex)
      const lift = Math.max(0, 1 - near) * 0.55

      ctx.strokeStyle = rgba(pal.ink, 1)
      strokeLoop(r.pts, z, Math.min(1, (r.opacity + lift * 0.5) * local), r.weight, r.gap)

      if (lift > 0.02) {
        ctx.strokeStyle = rgba(pal.accent, 1)
        strokeLoop(r.pts, z, 0.35 * lift * local, r.weight * 0.9, r.gap)
      }

      // Caustic sweep + tracking specular, shallow rings only. This is the
      // substitute for real refraction; it reads as surface.
      if (ringIndex <= 2) {
        const sweep = (Math.sin(t * 0.00035) + 1) / 2
        ctx.strokeStyle = rgba(pal.ink, 1)
        const n = r.pts.length
        for (let i = 0; i < n; i++) {
          const [x, y] = r.pts[i]
          const p = project(x, y, z, cam)
          if (p.depth <= NEAR) continue
          const u = p.x / w, v = p.y / h
          const d = Math.hypot(u - lightX, v - lightY)
          const spec = Math.max(0, 1 - d * 2.6)
          const caus = Math.max(0, Math.sin((i / n) * Math.PI * 6 + sweep * 6.28)) * 0.35
          const a = (spec * 0.5 + caus * 0.18) * local * r.opacity
          if (a < 0.02) continue
          ctx.globalAlpha = Math.min(0.8, a)
          ctx.lineWidth = r.weight * 1.4
          ctx.beginPath()
          ctx.arc(p.x, p.y, r.weight * 0.9, 0, Math.PI * 2)
          ctx.stroke()
        }
        ctx.globalAlpha = 1
      }
    }

    const drawIsland = (entry: number) => {
      const local = Math.min(1, Math.max(0, entry / 0.30))
      if (local <= 0) return
      const coast = rings[0]
      ctx.beginPath()
      let started = false
      for (let i = 0; i <= coast.pts.length; i++) {
        const [x, y] = coast.pts[i % coast.pts.length]
        const p = project(x, y, 0, cam)
        if (p.depth <= NEAR) continue
        if (!started) { ctx.moveTo(p.x, p.y); started = true } else { ctx.lineTo(p.x, p.y) }
      }
      ctx.closePath()
      ctx.globalAlpha = 0.30 * local
      ctx.fillStyle = rgba(pal.ink, 1)
      ctx.fill()
      ctx.globalAlpha = 1
    }

    /**
     * EEZ annotation.
     *
     * The ring itself is deliberately NOT drawn. At this camera the boundary is
     * ~15 island radii out, so it lands thousands of pixels off-frame; the only
     * way to show it as a closed arc would be to shrink it until it implied the
     * zone is roughly four times the island, which is false by three orders of
     * magnitude. A single dashed line crossing empty space read as a rendering
     * artifact, so it is stated as an annotation instead of drawn dishonestly.
     *
     * Figure is F9 in research/VERIFIED_FACTS.md, verbatim from the Ministry of
     * Blue Economy. It includes the Chagos region, which is why nothing here
     * characterises sovereignty.
     */
    const drawEezNote = (entry: number) => {
      const local = Math.min(1, Math.max(0, (entry - 0.55) / 0.4))
      if (local <= 0) return
      // Wide screens only. At phone widths it lands behind the card and bleeds
      // through as noise, and there is no clear space to move it to.
      if (w < 900) return
      const right = w - 40
      const top = h - 108
      ctx.textAlign = 'right'
      ctx.globalAlpha = 0.30 * local
      ctx.strokeStyle = rgba(pal.ink, 1)
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(right - 250, top - 14)
      ctx.lineTo(right, top - 14)
      ctx.stroke()

      ctx.fillStyle = rgba(pal.ink, 1)
      ctx.globalAlpha = 0.62 * local
      ctx.font = `600 12px ${monoFont}`
      ctx.fillText('EXCLUSIVE ECONOMIC ZONE', right, top + 6)
      ctx.globalAlpha = 0.86 * local
      ctx.font = `600 26px ${monoFont}`
      ctx.fillText('2 300 000 km²', right, top + 38)
      ctx.globalAlpha = 0.42 * local
      ctx.font = `500 11px ${monoFont}`
      ctx.fillText('EXTENDS FAR BEYOND THIS FRAME', right, top + 58)
      ctx.globalAlpha = 1
      ctx.textAlign = 'center'
    }

    /** Records placed label boxes so nothing overlaps anything else. */
    let boxes: Array<[number, number, number, number]> = []
    const fits = (x: number, y: number, wd: number, ht: number) => {
      const pad = 6
      for (const [bx, by, bw, bh] of boxes) {
        if (x - wd / 2 - pad < bx + bw / 2 && x + wd / 2 + pad > bx - bw / 2
          && y - ht - pad < by + 2 && y + pad > by - bh) return false
      }
      return true
    }

    const drawLabels = (entry: number) => {
      const local = Math.min(1, Math.max(0, (entry - 0.62) / 0.35))
      if (local <= 0) return
      boxes = []
      ctx.textAlign = 'center'
      ctx.textBaseline = 'alphabetic'

      // Place labels first - they matter more than depth figures, so they win
      // the space. Each sits OUTSIDE the coastline in open water with a
      // hairline leader back to its actual location, rather than on the island
      // where it was previously unreadable.
      for (const pl of places) {
        const p = project(pl.w[0], pl.w[1], 0, cam)
        if (p.depth <= NEAR) continue
        // Push outward, away from the island centre.
        const c = project(0, 0, 0, cam)
        const dx = p.x - c.x, dy = p.y - c.y
        const len = Math.max(1, Math.hypot(dx, dy))
        const off = 46
        const lx = p.x + (dx / len) * off
        const ly = p.y + (dy / len) * off

        const size = 13
        ctx.font = `500 ${size}px ${monoFont}`
        const tw = ctx.measureText(pl.name).width
        if (!fits(lx, ly, tw, size)) continue
        boxes.push([lx, ly, tw, size])

        ctx.globalAlpha = 0.34 * local
        ctx.strokeStyle = rgba(pal.ink, 1)
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(p.x, p.y)
        ctx.lineTo(lx - (dx / len) * 8, ly - (dy / len) * 8)
        ctx.stroke()

        ctx.globalAlpha = 0.9 * local
        ctx.fillStyle = rgba(pal.ink, 1)
        ctx.beginPath()
        ctx.arc(p.x, p.y, 2, 0, Math.PI * 2)
        ctx.fill()
        ctx.fillText(pl.name, lx, ly + 4)
      }

      // Depth labels sit ON their ring, offset PERPENDICULAR to the line so the
      // stroke never runs through the text. Any that would collide is skipped.
      for (const r of rings) {
        if (!r.label) continue
        const z = -Math.pow(Math.abs(r.depth), 0.42) * 0.055
        const n = r.pts.length
        // Try a few positions around the ring and take the first clear one.
        for (const frac of [0.30, 0.42, 0.18, 0.55, 0.70]) {
          const i = Math.floor(n * frac)
          const [x, y] = r.pts[i]
          const [nx, ny] = r.pts[(i + 1) % n]
          const a = project(x, y, z, cam)
          const b = project(nx, ny, z, cam)
          if (a.depth <= NEAR || b.depth <= NEAR) continue
          // Perpendicular to the tangent, pushed outward.
          const tx = b.x - a.x, ty = b.y - a.y
          const tl = Math.max(1, Math.hypot(tx, ty))
          const px = -ty / tl, py = tx / tl
          const c = project(0, 0, 0, cam)
          const sign = ((a.x - c.x) * px + (a.y - c.y) * py) >= 0 ? 1 : -1
          const lx = a.x + px * 13 * sign
          const ly = a.y + py * 13 * sign

          const size = 12
          ctx.font = `500 ${size}px ${monoFont}`
          const tw = ctx.measureText(r.label).width
          if (!fits(lx, ly, tw, size)) continue
          boxes.push([lx, ly, tw, size])
          ctx.globalAlpha = 0.6 * local
          ctx.fillStyle = rgba(pal.ink, 1)
          ctx.fillText(r.label, lx, ly + 4)
          break
        }
      }
      ctx.globalAlpha = 1
    }

    const drawMotes = (t: number, entry: number) => {
      const local = Math.min(1, Math.max(0, (entry - 0.5) / 0.4))
      if (local <= 0) return
      ctx.fillStyle = rgba(pal.ink, 1)
      for (const m of motes) {
        const bob = Math.sin(t * 0.00012 + m.phase) * 0.06
        const p = project(m.x, m.y, m.z + bob, cam)
        if (p.depth <= NEAR) continue
        // Nearer motes are larger and brighter — the parallax cue.
        const size = Math.max(0.6, Math.min(2.2, 2.4 / p.depth))
        ctx.globalAlpha = Math.min(0.30, 0.22 / p.depth) * local
        ctx.beginPath()
        ctx.arc(p.x, p.y, size, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalAlpha = 1
    }

    /** One full frame. entry 0..1 through the opening move. */
    const frame = (t: number, entry: number) => {
      ctx.fillStyle = rgba(pal.paper, 1)
      ctx.fillRect(0, 0, w, h)

      // Camera dollies back and up during entry.
      const e = easeOut(Math.min(1, entry))
      cam.dist = ENTRY_DIST + (BASE_DIST - ENTRY_DIST) * e
      cam.height = ENTRY_HEIGHT + (BASE_HEIGHT - ENTRY_HEIGHT) * e
      cam.pitch = (ENTRY_PITCH + (BASE_PITCH - ENTRY_PITCH) * e) + curP
      cam.heading = drift + curH
      recentre()

      drawEezNote(entry)
      // Far rings first, near rings last.
      for (let i = rings.length - 1; i >= 0; i--) drawRing(rings[i], t, entry, i)
      drawIsland(entry)
      drawMotes(t, entry)
      drawLabels(entry)
    }

    /* ------------------------------------- reduced motion: one composed still */
    if (reduceMotion) {
      const still = () => {
        resize()
        // A deliberately chosen angle: slight heading so the island reads as
        // three-dimensional, and the pulse parked mid-travel so one mid-depth
        // ring is lit rather than the scene looking inert.
        curH = 6 * Math.PI / 180
        curP = 0
        drift = 0
        lightX = 0.34; lightY = 0.3
        frame(PULSE_PERIOD * 0.34, 1)
      }
      still()
      window.addEventListener('resize', still)
      return () => {
        window.removeEventListener('resize', still)
        document.documentElement.style.removeProperty('--onboard-ink')
        document.documentElement.removeAttribute('data-scene')
      }
    }

    /* ------------------------------------------------------------- animated */
    window.addEventListener('mousemove', onMouse, { passive: true })
    window.addEventListener('touchmove', onTouch, { passive: true })
    window.addEventListener('deviceorientation', onOrient)
    window.addEventListener('resize', resize)

    let raf = 0, last = 0, running = true
    const t0 = performance.now()

    const loop = (now: number) => {
      raf = requestAnimationFrame(loop)
      if (!running) return
      if (now - last < FRAME_MS) return
      last = now
      // Damped ease toward the pointer target — glides, never snaps.
      curH += (targetH - curH) * LERP
      curP += (targetP - curP) * LERP
      drift += IDLE_DRIFT
      const elapsed = now - t0
      frame(elapsed, Math.min(1, elapsed / ENTRY_MS))
    }
    raf = requestAnimationFrame(loop)

    const onVis = () => { running = document.visibilityState === 'visible' }
    document.addEventListener('visibilitychange', onVis)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('mousemove', onMouse)
      window.removeEventListener('touchmove', onTouch)
      window.removeEventListener('deviceorientation', onOrient)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVis)
      document.documentElement.style.removeProperty('--onboard-ink')
      document.documentElement.removeAttribute('data-scene')
    }
  }, [theme, reduceMotion])

  if (theme === 'sunlight') return null
  return <canvas ref={ref} className="lk-chart" aria-hidden="true" />
}
