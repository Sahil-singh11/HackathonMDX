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
import { inkForSky, rgba } from './chart'
import {
  EEZ_SCALE, PLACES, buildEez, buildMotes, buildRings, lonLatToWorld,
  paletteForHour, project, type Camera, type Ring,
} from './terrain'

const FRAME_MS = 1000 / 30
const ENTRY_MS = 1200
const PULSE_PERIOD = 8000

// Camera constants (see the plan table).
const BASE_PITCH = -30 * Math.PI / 180
const ENTRY_PITCH = -18 * Math.PI / 180
// The island has radius 1. Sitting far back is what makes it read as SMALL
// against a vast zone - the whole point of the theme. At the previous 1.55 the
// island filled half the frame, saying the opposite.
const BASE_DIST = 6.2
const ENTRY_DIST = 2.9
const CAM_HEIGHT = 2.2
// Near-plane cull. Points closer than this project to enormous coordinates and
// knot the deep rings where they pass behind the viewer.
const NEAR = 0.5
const FOV = 55 * Math.PI / 180
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
    const eez = buildEez()
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

    let w = 0, h = 0, dpr = 1
    const cam: Camera = {
      heading: 0, pitch: BASE_PITCH, dist: BASE_DIST, height: CAM_HEIGHT,
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
      cam.cx = w >= 900 ? w * 0.63 : w * 0.5
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
      cam.cy = (w >= 900 ? h * 0.40 : h * 0.26) - o.y
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

    const drawEez = (entry: number) => {
      const local = Math.min(1, Math.max(0, (entry - 0.45) / 0.4))
      if (local <= 0) return
      ctx.strokeStyle = rgba(pal.ink, 1)
      ctx.setLineDash([10, 14])
      strokeLoop(eez, -0.62, 0.20 * local, 1.0)
      ctx.setLineDash([])

      // Label it on the ring itself. The figure is registered as F9 in
      // research/VERIFIED_FACTS.md, sourced verbatim from the Ministry of Blue
      // Economy; it includes the Chagos region, which is why the app never
      // characterises sovereignty anywhere.
      const p = project(0, -EEZ_SCALE * 1.0, -0.62, cam)
      if (p.depth > NEAR) {
        ctx.globalAlpha = 0.5 * local
        ctx.fillStyle = rgba(pal.ink, 1)
        ctx.font = `500 13px ${monoFont}`
        ctx.textAlign = 'center'
        ctx.fillText('EXCLUSIVE ECONOMIC ZONE  ·  2.3 MILLION KM²', p.x, p.y - 10)
        ctx.globalAlpha = 1
      }
    }

    const drawLabels = (entry: number) => {
      const local = Math.min(1, Math.max(0, (entry - 0.62) / 0.35))
      if (local <= 0) return
      ctx.textAlign = 'center'

      // Depth labels sit ON their ring and scale with distance.
      for (const r of rings) {
        if (!r.label) continue
        const z = -Math.pow(Math.abs(r.depth), 0.42) * 0.055
        const idx = Math.floor(r.pts.length * 0.62)
        const [x, y] = r.pts[idx]
        const p = project(x, y, z, cam)
        if (p.depth <= NEAR) continue
        const size = Math.max(8, Math.min(15, (cam.f / p.depth) * 0.014))
        ctx.globalAlpha = 0.42 * local
        ctx.fillStyle = rgba(pal.ink, 1)
        ctx.font = `500 ${size}px ${monoFont}`
        ctx.fillText(r.label, p.x, p.y - 4)
      }

      // Real places near the island. Once the island is small these collide
      // into an unreadable smudge, so drop any label too close to one already
      // placed - better to show three legible names than five overlapping.
      const placed: Array<[number, number]> = []
      for (const pl of places) {
        const p = project(pl.w[0], pl.w[1], 0, cam)
        if (p.depth <= NEAR) continue
        if (placed.some(([px, py]) => Math.hypot(px - p.x, py - p.y) < 92)) continue
        placed.push([p.x, p.y])
        const size = Math.max(9, Math.min(13, (cam.f / p.depth) * 0.012))
        ctx.globalAlpha = 0.62 * local
        ctx.fillStyle = rgba(pal.ink, 1)
        ctx.font = `500 ${size}px ${monoFont}`
        ctx.fillText(pl.name, p.x, p.y - 7)
        ctx.globalAlpha = 0.8 * local
        ctx.beginPath()
        ctx.arc(p.x, p.y, 1.6, 0, Math.PI * 2)
        ctx.fill()
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
      cam.pitch = (ENTRY_PITCH + (BASE_PITCH - ENTRY_PITCH) * e) + curP
      cam.heading = drift + curH
      recentre()

      drawEez(entry)
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
    }
  }, [theme, reduceMotion])

  if (theme === 'sunlight') return null
  return <canvas ref={ref} className="lk-chart" aria-hidden="true" />
}
