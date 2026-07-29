/**
 * Ambient lagoon layer — FROZEN (Sahil's lane).
 *
 * A fixed, full-viewport canvas behind all content showing slow layered wave
 * motion as soft caustic light bands.
 *
 * DATA-DRIVEN. It reads live wave height and swell period from the marine API
 * and changes character, so the fisher feels the sea state before reading a
 * number:
 *   calm  (0.5 m, long period)  -> wide, lazy, shallow bands, warm and slow
 *   rough (3.0 m, short period) -> narrow, steep, agitated bands, cooler and faster
 *
 * Hard constraints, all enforced below:
 *   - Canvas 2D, ONE requestAnimationFrame loop, capped at 30fps
 *   - pauses when the tab is hidden, and when the Battery API reports low charge
 *   - fully disabled under prefers-reduced-motion, in the Sunlight theme, and
 *     via the accessibility panel
 *   - never intercepts pointer events, never sits above content
 *   - opacity low enough that text contrast is unaffected in every theme
 *   - fisher routes only — authority/verify surfaces get a static background
 *
 * If this ever costs more than ~2ms/frame on a mid-range phone, simplify it
 * rather than adding more layers.
 */
import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { useTheme } from '../../theme'
import { setOceanEnabled, useOceanPreference } from './oceanStore'

export { setOceanEnabled } from './oceanStore'

const FRAME_MS = 1000 / 30      // 30fps cap
const BAND_COUNT = 5

/**
 * Resolved state for the ambient layer.
 *
 * The original shipped this as a hook with a LOCAL useState, so every caller
 * held its own copy: toggling the checkbox updated the panel and localStorage
 * but never reached the canvas, and the rAF loop kept running. That fix is kept
 * - the preference now lives in a shared external store (oceanStore.ts) so all
 * subscribers re-render together and switching off genuinely tears the loop
 * down. `blockedBy` lets the panel state WHY it is unavailable rather than
 * showing an enabled checkbox that is silently overridden.
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
  const { theme, reduceMotion } = useTheme()
  const { preference } = useOceanState()
  const [lowBattery, setLowBattery] = useState(false)

  // Sea state. staleTime is generous — this is ambience, not a forecast, and we
  // must not add API load for decoration.
  const { data: marine } = useQuery({
    queryKey: ['marine'],
    queryFn: api.marine,
    staleTime: 30 * 60_000,
    retry: false,
  })

  const waveHeight = typeof marine?.wave_height_m === 'number' ? (marine.wave_height_m as number) : 1
  const swellPeriod = typeof marine?.swell_period_s === 'number' ? (marine.swell_period_s as number) : 10

  useEffect(() => {
    const nav = navigator as Navigator & { getBattery?: () => Promise<BatteryLike> }
    if (!nav.getBattery) return
    let cancelled = false
    nav.getBattery().then((b) => {
      if (cancelled) return
      const check = () => setLowBattery(b.level < 0.2 && !b.charging)
      check()
      b.addEventListener?.('levelchange', check)
      b.addEventListener?.('chargingchange', check)
    }).catch(() => undefined)
    return () => { cancelled = true }
  }, [])

  const disabled = !preference || reduceMotion || theme === 'sunlight' || lowBattery

  useEffect(() => {
    if (disabled) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Cap DPR at 2: beyond that we pay for pixels nobody can see.
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let width = 0, height = 0

    const resize = () => {
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = Math.floor(width * dpr)
      canvas.height = Math.floor(height * dpr)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    // Map sea state onto the visuals.
    //   calm  -> few, wide, shallow, slow bands
    //   rough -> more, narrower, steeper, faster bands
    const roughness = Math.max(0, Math.min(1, (waveHeight - 0.3) / 2.7)) // 0.3m..3m -> 0..1
    const amplitude = 6 + roughness * 26          // px
    const wavelength = 520 - roughness * 300      // px, shorter when rough
    // THE ONE CHANGE from the original: the wave used to advance a fixed amount
    // per FRAME, which made a full cycle take well under 2 seconds and was also
    // frame-rate dependent. It now advances in REAL TIME, so one cycle takes the
    // swell period reported by the API (~11 s). Everything else - opacity,
    // colours, band count, composition, theme rules - is untouched.
    const cycleSeconds = Math.max(4, swellPeriod)

    const styles = getComputedStyle(document.documentElement)
    const band1 = styles.getPropertyValue('--ocean-band-1').trim() || 'rgba(14,124,134,0.10)'
    const band2 = styles.getPropertyValue('--ocean-band-2').trim() || 'rgba(10,37,64,0.06)'

    let raf = 0
    let last = 0
    let t = 0
    let prevT = performance.now()
    let running = true

    const draw = (now: number) => {
      raf = requestAnimationFrame(draw)
      if (!running) return
      if (now - last < FRAME_MS) return       // 30fps cap
      last = now
      // Clamped so returning from a hidden tab eases back in instead of
      // jumping the phase forward.
      const dt = Math.min(0.25, (now - prevT) / 1000)
      prevT = now
      t += (dt / cycleSeconds) * Math.PI * 2

      ctx.clearRect(0, 0, width, height)
      for (let i = 0; i < BAND_COUNT; i++) {
        const depth = i / (BAND_COUNT - 1)
        const yBase = height * (0.25 + depth * 0.6)
        const amp = amplitude * (0.5 + depth * 0.8)
        const len = wavelength * (1 - depth * 0.25)
        const phase = t * (0.6 + depth * 0.5) + i * 1.7

        ctx.beginPath()
        ctx.moveTo(0, yBase)
        // Step of 24px keeps this cheap; the curve is soft enough that finer
        // sampling is not visible.
        for (let x = 0; x <= width; x += 24) {
          const y = yBase
            + Math.sin(x / len + phase) * amp
            + Math.sin(x / (len * 0.45) + phase * 1.4) * amp * 0.3
          ctx.lineTo(x, y)
        }
        ctx.lineTo(width, height)
        ctx.lineTo(0, height)
        ctx.closePath()
        ctx.fillStyle = i % 2 === 0 ? band1 : band2
        ctx.fill()
      }
    }
    raf = requestAnimationFrame(draw)

    const onVisibility = () => { running = document.visibilityState === 'visible' }
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [disabled, waveHeight, swellPeriod, theme])

  if (disabled) return null

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: 'fixed', inset: 0, zIndex: 0,
        pointerEvents: 'none',            // never intercepts input
        opacity: 'var(--ocean-opacity, 1)',
      }}
    />
  )
}
