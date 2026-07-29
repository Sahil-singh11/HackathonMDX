/**
 * The living nautical chart behind the onboarding card.
 *
 * Four layers, back to front: sky/horizon, water plane, bathymetric contours
 * around Mauritius, and depth soundings.
 *
 * Constraints held here (all checked in the Landing verification pass):
 *   - Canvas 2D only. No WebGL, no libraries, no new dependencies.
 *   - ONE requestAnimationFrame loop, capped at 30fps, paused when the tab is
 *     hidden.
 *   - aria-hidden and pointer-events: none. It carries no information and can
 *     never intercept a tap.
 *   - prefers-reduced-motion draws ONE fully-composed still frame — every
 *     contour, every sounding, the finished picture — and then stops. That
 *     still is a deliberate design, not a degraded fallback, because a lot of
 *     people will only ever see it.
 *   - Sunlight theme renders nothing at all; the page falls back to flat white.
 *     Legibility in direct sun beats beauty, without exception.
 *   - First paint does not wait on this: Landing renders the card immediately
 *     and this mounts alongside.
 */
import { useEffect, useRef } from 'react'
import { useTheme } from '../../theme'
import {
  SOUNDINGS, daylight, inkForSky, isoline, mix, rgba, readToken, skyForHour, tracePath,
} from './chart'

const FRAME_MS = 1000 / 30      // 30fps cap
const RING_COUNT = 6
const HORIZON = 0.38            // fraction of viewport height
const ENTRY_MS = 900            // contour draw-on
const PULSE_PERIOD = 8000       // depth sounding returns every 8s

export function NauticalChart({ warm = 0 }: { warm?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const { theme, reduceMotion } = useTheme()
  // Kept in a ref so a language selection re-warms the horizon WITHOUT
  // restarting the animation or re-running the entry sequence.
  const warmRef = useRef(warm)
  warmRef.current = warm

  useEffect(() => {
    // Sunlight: no canvas at all.
    if (theme === 'sunlight') return
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let w = 0, h = 0

    const resize = () => {
      w = window.innerWidth
      h = window.innerHeight
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()

    // --- palette, resolved once per theme -------------------------------
    const hour = new Date().getHours() + new Date().getMinutes() / 60
    const sky = skyForHour(hour)
    const day = daylight(hour)
    const foam = readToken('--foam')
    const lagoon = readToken('--lagoon')
    const accent = readToken('--accent')
    const muted = readToken('--text-muted')
    const band1 = readToken('--ocean-band-1', lagoon)
    const band2 = readToken('--ocean-band-2', foam)

    // Contours pull back when the sky is bright so they never fight it, and
    // sit stronger at night when they are carrying the whole image.
    const contourAlpha = 0.55 - day * 0.18
    const soundingAlpha = 0.34 - day * 0.10

    // Text that sits directly on the sky (the masthead) needs an ink chosen
    // against the SKY, not against the theme surface - see inkForSky().
    const ink = inkForSky(sky.zenith)
    document.documentElement.style.setProperty('--onboard-ink', rgba(ink, 1))

    // Island sits right-of-centre on wide screens so the card can take the
    // left. On narrow screens it lifts above the card instead of behind it.
    const layout = () => {
      const narrow = w < 900
      return {
        cx: narrow ? w * 0.5 : w * 0.72,
        cy: narrow ? h * 0.22 : h * 0.54,
        scale: narrow ? Math.min(w, h) * 0.13 : Math.min(w, h) * 0.17,
      }
    }

    const drawSky = () => {
      const warmth = warmRef.current
      const g = ctx.createLinearGradient(0, 0, 0, h * HORIZON)
      const zen = sky.zenith
      // Selecting a language warms the horizon very slightly - a small
      // acknowledgement that a decision was made, not a colour change.
      const hor = warmth > 0 ? mix(sky.horizon, readToken('--coral-soft'), warmth * 0.18) : sky.horizon
      g.addColorStop(0, rgba(zen, 1))
      g.addColorStop(1, rgba(hor, 1))
      ctx.fillStyle = g
      ctx.fillRect(0, 0, w, h * HORIZON)

      // Water body below the horizon, a shade deeper than the sky meets it.
      const wg = ctx.createLinearGradient(0, h * HORIZON, 0, h)
      wg.addColorStop(0, rgba(mix(hor, zen, 0.35), 1))
      wg.addColorStop(1, rgba(mix(zen, readToken('--abyss'), 0.5), 1))
      ctx.fillStyle = wg
      ctx.fillRect(0, h * HORIZON, w, h * (1 - HORIZON))

      // The horizon itself: a hairline, brighter at dawn/dusk.
      ctx.strokeStyle = rgba(mix(hor, foam, 0.5), 0.35)
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, Math.round(h * HORIZON) + 0.5)
      ctx.lineTo(w, Math.round(h * HORIZON) + 0.5)
      ctx.stroke()
    }

    const drawWater = (t: number) => {
      // Three sine-layered bands drifting at different speeds. Slow: this is a
      // lagoon at rest, not a screensaver.
      const top = h * HORIZON
      for (let i = 0; i < 3; i++) {
        const depth = i / 2
        const y = top + (h - top) * (0.18 + depth * 0.34)
        const amp = 5 + depth * 9
        const len = 420 - depth * 120
        const phase = t * (0.00006 + depth * 0.00004)
        ctx.beginPath()
        ctx.moveTo(0, y)
        for (let x = 0; x <= w; x += 28) {
          ctx.lineTo(x, y + Math.sin(x / len + phase) * amp + Math.sin(x / (len * 0.4) + phase * 1.6) * amp * 0.3)
        }
        ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath()
        // Use the token's OWN alpha (0.05-0.14). Forcing 1 here previously
        // painted opaque slabs over the water gradient instead of ripples.
        const bandTok = i % 2 === 0 ? band1 : band2
        ctx.fillStyle = rgba(bandTok, bandTok.a ?? 0.1)
        ctx.fill()
      }

      // Specular glints: deterministic points ON the wave crests that brighten
      // and fade with the wave phase, so they are a property of the water
      // rather than sprites floating over it.
      const glintPhase = t * 0.00006
      for (let i = 0; i < 14; i++) {
        const gx = ((i * 137.5) % 100) / 100 * w
        const gy = top + (h - top) * (0.2 + ((i * 61.8) % 100) / 100 * 0.7)
        const crest = Math.sin(gx / 300 + glintPhase + i)
        if (crest < 0.72) continue
        const a = (crest - 0.72) / 0.28 * (0.14 - day * 0.06)
        ctx.fillStyle = rgba(foam, Math.max(0, a))
        ctx.fillRect(gx, gy, 14 + crest * 10, 1)
      }
    }

    const drawContours = (t: number, entry: number) => {
      const { cx, cy, scale } = layout()
      // Pulse travels OUTWARD from the island, like a depth sounding returning.
      const pulse = (t % PULSE_PERIOD) / PULSE_PERIOD
      for (let r = 0; r < RING_COUNT; r++) {
        // Outermost ring draws first during entry, innermost last.
        const ringStart = (RING_COUNT - 1 - r) / RING_COUNT * 0.65
        const local = Math.min(1, Math.max(0, (entry - ringStart) / 0.35))
        if (local <= 0) continue

        const spread = r
        const near = Math.abs(pulse * RING_COUNT * 1.15 - r)
        const lift = Math.max(0, 1 - near) * 0.5   // ring brightens as the pulse passes
        const base = contourAlpha * (1 - r / (RING_COUNT + 2))

        ctx.strokeStyle = rgba(
          mix(lagoon, foam, r / RING_COUNT),
          Math.min(0.85, (base + base * lift) * local),
        )
        ctx.lineWidth = r === 0 ? 1.25 : 0.9
        tracePath(ctx, isoline(spread), cx, cy, scale, local)
        ctx.stroke()

        if (lift > 0.02) {
          ctx.strokeStyle = rgba(accent, 0.55 * lift * local)
          ctx.lineWidth = 0.75
          ctx.stroke()
        }
      }

      // The island itself: a filled hairline mass, the only solid on the chart.
      const localIsland = Math.min(1, Math.max(0, (entry - 0.6) / 0.3))
      if (localIsland > 0) {
        tracePath(ctx, isoline(0), cx, cy, scale)
        ctx.fillStyle = rgba(mix(lagoon, foam, 0.25), 0.22 * localIsland)
        ctx.fill()
        ctx.strokeStyle = rgba(foam, 0.75 * localIsland)
        ctx.lineWidth = 1.5
        ctx.stroke()
      }
    }

    const drawSoundings = (entry: number) => {
      const local = Math.min(1, Math.max(0, (entry - 0.75) / 0.35))
      if (local <= 0) return
      const { cx, cy, scale } = layout()
      ctx.font = `500 ${Math.max(10, scale * 0.075)}px ${getComputedStyle(document.documentElement).getPropertyValue('--font-data') || 'monospace'}`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = rgba(muted, soundingAlpha * local)
      for (const s of SOUNDINGS) {
        const rad = (1 + s.ring * 0.42) * scale
        ctx.fillText(String(s.depth), cx + Math.sin(s.angle) * rad, cy - Math.cos(s.angle) * rad)
      }
    }

    /** One complete frame. entry: 0..1 through the draw-on sequence. */
    const frame = (t: number, entry: number) => {
      ctx.clearRect(0, 0, w, h)
      drawSky()
      drawWater(t)
      drawContours(t, entry)
      drawSoundings(entry)
    }

    // --- reduced motion: one composed still frame, then stop --------------
    if (reduceMotion) {
      // entry = 1 so the chart is fully drawn; a fixed t picks a pleasing
      // wave phase and places the pulse mid-travel so a ring is lit.
      frame(PULSE_PERIOD * 0.42, 1)
      const onResize = () => { resize(); frame(PULSE_PERIOD * 0.42, 1) }
      window.addEventListener('resize', onResize)
      return () => {
        window.removeEventListener('resize', onResize)
        document.documentElement.style.removeProperty('--onboard-ink')
      }
    }

    // --- animated ---------------------------------------------------------
    let raf = 0
    let last = 0
    let running = true
    const t0 = performance.now()

    const loop = (now: number) => {
      raf = requestAnimationFrame(loop)
      if (!running) return
      if (now - last < FRAME_MS) return
      last = now
      const elapsed = now - t0
      frame(elapsed, Math.min(1, elapsed / ENTRY_MS))
    }
    raf = requestAnimationFrame(loop)

    const onVisibility = () => { running = document.visibilityState === 'visible' }
    const onResize = () => resize()
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('resize', onResize)
      document.documentElement.style.removeProperty('--onboard-ink')
    }
  }, [theme, reduceMotion])

  if (theme === 'sunlight') return null

  return <canvas ref={ref} className="lk-chart" aria-hidden="true" />
}
