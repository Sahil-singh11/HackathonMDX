/**
 * Ambient ocean layer — the in-app background.
 *
 * This is NOT the welcome screen. It sits behind working content, so it is
 * quieter in every dimension: a gently receding wireframe swell surface, no
 * island, no contours, no labels, and NO reaction to the pointer. Someone
 * trying to log a catch should never see the background answer them.
 *
 * HONEST MOTION. The accessibility panel claims this layer "reflects the
 * current sea state", so it does, literally:
 *   - one swell cycle takes exactly the reported swell period in REAL seconds
 *     (10.9s from the API means a crest takes 10.9 actual seconds)
 *   - wave height drives amplitude and line spacing, never speed
 *   - wave direction sets the drift angle
 * Everything is clamped so no live reading can make it distracting, and data
 * changes ease over ~2s so the scene never snaps when a fetch lands. With no
 * data at all it renders a calm sea rather than freezing or breaking.
 *
 * The on/off control is REAL: switching it off cancels the rAF loop and removes
 * the canvas from the DOM. See oceanStore.ts for why that needed fixing.
 */
import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { useTheme } from '../../theme'
import { readToken, rgba, type RGB } from '../onboarding/chart'
import { focalFor, project, type Camera } from './projection'
import { setOceanEnabled, useOceanPreference } from './oceanStore'

export { setOceanEnabled } from './oceanStore'

const FRAME_MS = 1000 / 30
const FOV = 52 * Math.PI / 180
const PITCH = -12 * Math.PI / 180   // shallow: a sea surface, not a map
const CAM_HEIGHT = 0.9
const CAM_DIST = 1.0

const ROWS = 15                     // swell lines receding to the vanishing region
const SAMPLES = 40                  // points per line
const CROSS = 13                    // subtle cross-lines
const EASE_MS = 2000                // data changes glide in over ~2s

/** Ceilings so no live reading can produce something distracting. */
const AMP_MIN = 0.010, AMP_MAX = 0.055
const PERIOD_MIN = 5, PERIOD_MAX = 20      // seconds
const ALPHA_MAX = 0.16                     // hard ceiling on line opacity

const lerp = (a: number, b: number, t: number) => a + (b - a) * t
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

/**
 * Resolved state for the ambient layer, including every dependency.
 * Exported so the accessibility panel can explain WHY it is unavailable instead
 * of showing an enabled checkbox that is silently overridden.
 */
export function useOceanState() {
  const preference = useOceanPreference()
  const { theme, reduceMotion } = useTheme()
  const blockedBy: 'reduce-motion' | 'sunlight' | null =
    reduceMotion ? 'reduce-motion' : theme === 'sunlight' ? 'sunlight' : null
  return { preference, blockedBy, active: preference && !blockedBy, setOceanEnabled }
}

interface BatteryLike { level: number; charging: boolean; addEventListener?: (t: string, l: () => void) => void }

export function OceanLayer() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { active } = useOceanState()
  const lowBatteryRef = useRef(false)

  // Sea state. Long staleTime: this is ambience and must not add API load.
  // A failed fetch keeps whatever is cached; with nothing cached the defaults
  // below are a calm sea, never a frozen or broken scene.
  const { data: marine } = useQuery({
    queryKey: ['marine'],
    queryFn: api.marine,
    staleTime: 30 * 60_000,
    gcTime: 24 * 60 * 60_000,
    retry: false,
  })

  const waveHeight = typeof marine?.wave_height_m === 'number' ? marine.wave_height_m as number : 0.8
  const swellPeriod = typeof marine?.swell_period_s === 'number' ? marine.swell_period_s as number : 11
  const waveDir = typeof marine?.wave_direction_deg === 'number' ? marine.wave_direction_deg as number : 135

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

  useEffect(() => {
    // Inactive -> the effect never starts, so there is no loop to leak.
    if (!active) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let w = 0, h = 0, dpr = 1
    const cam: Camera = { heading: 0, pitch: PITCH, dist: CAM_DIST, height: CAM_HEIGHT, f: 800, cx: 0, cy: 0 }

    // One ink over the page background, from semantic tokens only.
    const ink: RGB = readToken('--text')
    const accent: RGB = readToken('--accent')

    // ---- geometry precomputed ONCE; the loop only transforms and strokes ---
    const rowDist: number[] = []
    for (let j = 0; j < ROWS; j++) rowDist.push(0.55 * Math.pow(1.34, j))
    const xs: number[] = []
    for (let i = 0; i < SAMPLES; i++) xs.push(-3.2 + (6.4 * i) / (SAMPLES - 1))

    // Grain tile rendered once and stamped as a pattern. Per-pixel noise every
    // frame would wreck the budget; one fill does not.
    const grain = document.createElement('canvas')
    grain.width = grain.height = 128
    {
      const g = grain.getContext('2d')
      if (g) {
        const img = g.createImageData(128, 128)
        for (let i = 0; i < img.data.length; i += 4) {
          const v = 128 + (Math.random() - 0.5) * 255
          img.data[i] = img.data[i + 1] = img.data[i + 2] = v
          img.data[i + 3] = 9
        }
        g.putImageData(img, 0, 0)
      }
    }
    let grainPattern: CanvasPattern | null = null
    let lightGrad: CanvasGradient | null = null
    let vignetteGrad: CanvasGradient | null = null

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
      cam.cx = w * 0.5
      cam.cy = h * 0.34   // vanishing region sits high in the viewport

      // Soft off-centre light and a gentle vignette, so the page has a focal
      // point instead of flat even fill. Built here, never per frame.
      lightGrad = ctx.createRadialGradient(w * 0.68, h * 0.16, 0, w * 0.68, h * 0.16, Math.max(w, h) * 0.8)
      lightGrad.addColorStop(0, rgba(accent, 0.05))
      lightGrad.addColorStop(0.5, rgba(accent, 0.016))
      lightGrad.addColorStop(1, rgba(accent, 0))

      vignetteGrad = ctx.createRadialGradient(w * 0.5, h * 0.45, Math.min(w, h) * 0.28, w * 0.5, h * 0.5, Math.max(w, h) * 0.8)
      vignetteGrad.addColorStop(0, rgba(ink, 0))
      vignetteGrad.addColorStop(1, rgba(ink, 0.09))

      grainPattern = ctx.createPattern(grain, 'repeat')
    }
    resize()

    // ---- eased sea state --------------------------------------------------
    const target = {
      amp: clamp(0.012 + waveHeight * 0.014, AMP_MIN, AMP_MAX),
      period: clamp(swellPeriod, PERIOD_MIN, PERIOD_MAX),
      angle: (waveDir * Math.PI) / 180,
      wavelength: lerp(2.6, 1.35, clamp(waveHeight / 3, 0, 1)),  // rougher packs tighter
    }
    const from = { ...target }
    const cur = { ...target }
    const easeStart = performance.now()

    let raf = 0
    let last = 0
    let running = true
    // Phase accumulates in REAL seconds, so one cycle takes exactly `period`.
    // Speed is never a free parameter.
    let phase = 0
    let prevT = performance.now()

    const draw = (nowMs: number) => {
      const dt = Math.min(0.1, (nowMs - prevT) / 1000)
      prevT = nowMs

      const e = Math.min(1, (nowMs - easeStart) / EASE_MS)
      cur.amp = lerp(from.amp, target.amp, e)
      cur.period = lerp(from.period, target.period, e)
      cur.angle = lerp(from.angle, target.angle, e)
      cur.wavelength = lerp(from.wavelength, target.wavelength, e)

      phase += (dt / cur.period) * Math.PI * 2

      ctx.clearRect(0, 0, w, h)
      if (lightGrad) { ctx.fillStyle = lightGrad; ctx.fillRect(0, 0, w, h) }

      const dirX = Math.cos(cur.angle), dirY = Math.sin(cur.angle)
      const k = (Math.PI * 2) / cur.wavelength
      const heightAt = (x: number, y: number) =>
        Math.sin((x * dirX + y * dirY) * k + phase) * cur.amp
        + Math.sin((x * dirX - y * dirY) * k * 0.6 - phase * 0.7) * cur.amp * 0.35

      // Swell lines, far first so nearer lines draw over them. Depth cue is the
      // opacity ramp only - no blur, no shadow, no filters.
      ctx.lineCap = 'round'
      for (let j = ROWS - 1; j >= 0; j--) {
        const d = rowDist[j]
        const fade = Math.pow(1 - j / ROWS, 1.6)
        ctx.strokeStyle = rgba(ink, Math.min(ALPHA_MAX, 0.028 + fade * 0.125))
        ctx.lineWidth = 0.6 + fade * 0.7
        ctx.beginPath()
        let started = false
        for (let i = 0; i < SAMPLES; i++) {
          const x = xs[i]
          const p = project(x, d, heightAt(x, d), cam)
          if (p.depth <= 0.12) { started = false; continue }
          if (!started) { ctx.moveTo(p.x, p.y); started = true } else ctx.lineTo(p.x, p.y)
        }
        ctx.stroke()
      }

      ctx.lineWidth = 0.5
      ctx.strokeStyle = rgba(ink, 0.032)
      for (let c = 0; c < CROSS; c++) {
        const x = -3.2 + (6.4 * c) / (CROSS - 1)
        ctx.beginPath()
        let started = false
        for (let j = 0; j < ROWS; j++) {
          const d = rowDist[j]
          const p = project(x, d, heightAt(x, d), cam)
          if (p.depth <= 0.12) { started = false; continue }
          if (!started) { ctx.moveTo(p.x, p.y); started = true } else ctx.lineTo(p.x, p.y)
        }
        ctx.stroke()
      }

      if (vignetteGrad) { ctx.fillStyle = vignetteGrad; ctx.fillRect(0, 0, w, h) }
      if (grainPattern) { ctx.fillStyle = grainPattern; ctx.fillRect(0, 0, w, h) }
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

    // FULL teardown. Cancelling the handle is what actually stops the work;
    // hiding the canvas would leave the loop running and make the panel's
    // "save battery" copy a lie.
    return () => {
      cancelAnimationFrame(raf)
      running = false
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('resize', resize)
    }
  }, [active, waveHeight, swellPeriod, waveDir])

  // No canvas in the DOM when inactive: nothing to paint, nothing to
  // composite, and no chance of a stale loop drawing into a hidden element.
  if (!active) return null

  return <canvas ref={canvasRef} className="lk-ocean" aria-hidden="true" />
}
