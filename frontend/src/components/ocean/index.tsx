/**
 * Ambient layer — the corner of a chart the interface rests on.
 *
 * This is the SAME bathymetric terrain as the welcome screen, from the same
 * shared geometry and projection, just repositioned and dialled back: the
 * camera pushed far out, the island small and cropped by one corner of the
 * viewport, and only the deep contour rings sweeping through the frame.
 *
 * WHAT THIS REPLACED, and why: an earlier version drew generic horizontal
 * swell lines with procedural grain and a vignette. Directionless wavy lines at
 * low opacity read as noise rather than design, and grain over a light
 * background reads as dirt. Recognisable structure — closed contour rings,
 * crisp hairlines, a clear near/far ramp — is what makes the welcome screen
 * work, so this reuses that instead of inventing a second visual language.
 *
 * Rules this layer holds to:
 *   - CRISP, not faint. One clean 1px stroke at 8-10% opacity. No blur, no
 *     shadow, no filters: a sharp hairline at low opacity looks intentional,
 *     a soft one looks like a smudge.
 *   - NIGHT ONLY on content pages. The light background is where every one of
 *     these problems shows up worst, so Day and Sunlight get the flat surface
 *     token and nothing else.
 *   - CLEAR OF CONTENT. The rings live in the outer margins; the region behind
 *     the main content column is clipped out entirely.
 *   - No pointer reactivity of any kind. Someone logging a catch must never see
 *     the background answer them.
 *
 * The welcome screen keeps its own richer treatment in all themes; only this
 * in-app layer is restrained.
 */
import { useEffect, useRef, useState } from 'react'
import { useTheme } from '../../theme'
import { readToken, rgba, type RGB } from '../onboarding/chart'
import { buildRings } from '../onboarding/terrain'
import { focalFor, project, type Camera } from './projection'
import { setOceanEnabled, useOceanPreference } from './oceanStore'

export { setOceanEnabled } from './oceanStore'

const FRAME_MS = 1000 / 30
const FOV = 38 * Math.PI / 180
const PITCH = -62 * Math.PI / 180   // matches the welcome screen's camera
const CAM_HEIGHT = 5.5
/** Far further out than the welcome screen, so the island reads as a detail. */
const CAM_DIST = 26

/** Only the deep rings. The coastline and reef belong to the welcome screen. */
const FIRST_RING = 4

const STROKE_ALPHA = 0.09      // crisp hairline, deliberately in the 8-10% band
const PULSE_PERIOD = 14000     // very slow; this sits behind real work

export type OceanBlockedBy = 'reduce-motion' | 'sunlight' | 'day-theme' | null

/**
 * Resolved state for the ambient layer, including every dependency, so the
 * accessibility panel can explain WHY it is unavailable rather than showing an
 * enabled checkbox that is silently overridden.
 */
export function useOceanState() {
  const preference = useOceanPreference()
  const { theme, reduceMotion } = useTheme()
  const blockedBy: OceanBlockedBy =
    reduceMotion ? 'reduce-motion'
      : theme === 'sunlight' ? 'sunlight'
        : theme !== 'night' ? 'day-theme'
          : null
  return { preference, blockedBy, active: preference && !blockedBy, setOceanEnabled }
}

interface BatteryLike { level: number; charging: boolean; addEventListener?: (t: string, l: () => void) => void }

export function OceanLayer() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { active } = useOceanState()
  const lowBatteryRef = useRef(false)
  // Rect of the main content column, kept clear of contours.
  const [clearRect, setClearRect] = useState<DOMRect | null>(null)
  /**
   * On phone and tablet the content column spans the full viewport width, so
   * the clip leaves no margin to draw in. Running a 30fps loop that paints
   * nothing visible would waste battery on exactly the devices that can least
   * afford it, so the layer sits out entirely below that threshold.
   */
  const hasMargin = clearRect != null
    && clearRect.width > 0
    && (window.innerWidth - clearRect.width) >= 180

  useEffect(() => {
    const nav = navigator as Navigator & { getBattery?: () => Promise<BatteryLike> }
    if (!nav.getBattery) return
    let cancelled = false
    nav.getBattery().then((b) => {
      if (cancelled) return
      const check = () => { lowBatteryRef.current = b.level < 0.2 && !b.charging }
      check()
      b.addEventListener?.('levelchange', check)
      b.addEventListener?.('chargingchange', check)
    }).catch(() => undefined)
    return () => { cancelled = true }
  }, [])

  // Track the content column so the contours can be kept out from behind it.
  // A ResizeObserver keeps this correct across route changes and resizes
  // without reading layout every frame.
  useEffect(() => {
    if (!active) return
    const main = document.querySelector('main')
    if (!main) return
    const update = () => setClearRect(main.getBoundingClientRect())
    update()
    const ro = new ResizeObserver(update)
    ro.observe(main)
    window.addEventListener('scroll', update, { passive: true })
    return () => { ro.disconnect(); window.removeEventListener('scroll', update) }
  }, [active])

  useEffect(() => {
    if (!active || !hasMargin) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Shared geometry, precomputed once. Same module the welcome screen uses.
    const rings = buildRings().slice(FIRST_RING)
    const ink: RGB = readToken('--text')

    let w = 0, h = 0, dpr = 1
    const cam: Camera = { heading: 0, pitch: PITCH, dist: CAM_DIST, height: CAM_HEIGHT, f: 800, cx: 0, cy: 0 }

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = window.innerWidth
      h = window.innerHeight
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      cam.f = focalFor(h, FOV)
      // Island parked beyond the bottom-right corner, so only the outer rings
      // arc back into frame through the right and bottom margins.
      cam.cx = 0
      cam.cy = 0
      const o = project(0, 0, 0, cam)
      cam.cx = w * 1.06 - o.x
      cam.cy = h * 1.12 - o.y
    }
    resize()

    let raf = 0, last = 0, running = true
    const t0 = performance.now()

    const draw = (now: number) => {
      ctx.clearRect(0, 0, w, h)
      ctx.save()

      // Clip OUT the content column: everything outside it is drawable. Cards
      // are opaque, so this reads as a clean margin treatment rather than
      // lines stopping mid-stroke.
      if (clearRect && clearRect.width > 0) {
        ctx.beginPath()
        ctx.rect(0, 0, w, h)
        ctx.rect(clearRect.x - 8, clearRect.y - 8, clearRect.width + 16, clearRect.height + 16)
        ctx.clip('evenodd')
      }

      // A single slow brightening travelling outward through the rings. Much
      // slower than the welcome screen's, because this sits behind real work.
      const pulse = ((now - t0) % PULSE_PERIOD) / PULSE_PERIOD

      ctx.lineWidth = 1               // crisp hairline, never scaled
      for (let i = rings.length - 1; i >= 0; i--) {
        const r = rings[i]
        const z = -Math.pow(Math.abs(r.depth), 0.42) * 0.055
        const near = Math.abs(pulse * rings.length * 1.25 - i)
        const lift = Math.max(0, 1 - near) * 0.4
        // Near/far ramp: outer (deeper) rings sit fainter.
        const depthFade = 1 - (i / (rings.length + 1)) * 0.45
        ctx.strokeStyle = rgba(ink, STROKE_ALPHA * depthFade * (1 + lift))

        ctx.beginPath()
        let started = false
        const n = r.pts.length
        for (let k = 0; k <= n; k++) {
          const [x, y] = r.pts[k % n]
          const p = project(x, y, z, cam)
          if (p.depth <= 0.5) { started = false; continue }
          if (!started) { ctx.moveTo(p.x, p.y); started = true } else ctx.lineTo(p.x, p.y)
        }
        ctx.stroke()
      }
      ctx.restore()
    }

    const loop = (now: number) => {
      raf = requestAnimationFrame(loop)
      if (!running) return
      if (now - last < FRAME_MS) return
      last = now
      if (lowBatteryRef.current) return
      draw(now)
    }
    raf = requestAnimationFrame(loop)

    const onVisibility = () => { running = document.visibilityState === 'visible' }
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('resize', resize)

    return () => {
      cancelAnimationFrame(raf)
      running = false
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('resize', resize)
    }
  }, [active, hasMargin, clearRect])

  if (!active || !hasMargin) return null
  return <canvas ref={canvasRef} className="lk-ocean" aria-hidden="true" />
}
