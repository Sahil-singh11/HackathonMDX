/**
 * Theme + accessibility preference provider.  FROZEN after Phase 0.
 *
 * Owns four persisted user preferences and reflects them onto <html> as data
 * attributes, which is what styles/tokens.css and styles/base.css key off:
 *
 *   data-theme         day | night | sunlight
 *   data-night-vision  on  | off        (only meaningful inside night)
 *   data-text-scale    100 | 125 | 150
 *   data-reduce-motion on  | off
 *
 * Defaults come from the system (prefers-color-scheme, prefers-reduced-motion)
 * and are overridden by anything the user has explicitly chosen. Writing to
 * <html> rather than to React context means the legacy pages in styles.css get
 * themed too, without being wrapped in a provider.
 *
 * Usage:
 *   <ThemeProvider>…</ThemeProvider>          // once, at the app root
 *   const { theme, setTheme } = useTheme()    // anywhere below it
 */
import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
  type ReactNode,
} from 'react'

export type Theme = 'day' | 'night' | 'sunlight'
export type TextScale = '100' | '125' | '150'

export interface ThemePrefs {
  theme: Theme
  nightVision: boolean
  textScale: TextScale
  reduceMotion: boolean
}

export interface ThemeContextValue extends ThemePrefs {
  setTheme: (t: Theme) => void
  setNightVision: (v: boolean) => void
  setTextScale: (s: TextScale) => void
  setReduceMotion: (v: boolean) => void
  /** Cycles day -> night -> sunlight -> day. Used by the header toggle. */
  cycleTheme: () => void
  /** True when the OS asked for reduced motion, even if the user has not. */
  systemReduceMotion: boolean
}

const STORAGE_KEY = 'lamer-konekte-theme'

const THEME_ORDER: Theme[] = ['day', 'night', 'sunlight']

function prefersDark(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-color-scheme: dark)').matches === true
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
}

function loadPrefs(): ThemePrefs {
  const fallback: ThemePrefs = {
    theme: prefersDark() ? 'night' : 'day',
    nightVision: false,
    textScale: '100',
    reduceMotion: prefersReducedMotion(),
  }
  if (typeof localStorage === 'undefined') return fallback
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return fallback
    const saved = JSON.parse(raw) as Partial<ThemePrefs>
    return {
      theme: THEME_ORDER.includes(saved.theme as Theme) ? (saved.theme as Theme) : fallback.theme,
      nightVision: typeof saved.nightVision === 'boolean' ? saved.nightVision : fallback.nightVision,
      textScale: (['100', '125', '150'] as const).includes(saved.textScale as TextScale)
        ? (saved.textScale as TextScale) : fallback.textScale,
      // An explicit user choice wins, but the OS preference can only ever turn
      // motion OFF, never force it back on.
      reduceMotion: typeof saved.reduceMotion === 'boolean'
        ? saved.reduceMotion || fallback.reduceMotion
        : fallback.reduceMotion,
    }
  } catch {
    // Corrupt or unavailable storage must never break the app.
    return fallback
  }
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<ThemePrefs>(loadPrefs)
  const [systemReduceMotion, setSystemReduceMotion] = useState(prefersReducedMotion)

  // Reflect onto <html> so legacy pages are themed too, not just new components.
  useEffect(() => {
    const el = document.documentElement
    el.setAttribute('data-theme', prefs.theme)
    el.setAttribute('data-night-vision', prefs.theme === 'night' && prefs.nightVision ? 'on' : 'off')
    el.setAttribute('data-text-scale', prefs.textScale)
    el.setAttribute('data-reduce-motion', prefs.reduceMotion ? 'on' : 'off')
  }, [prefs])

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)) } catch { /* storage full or blocked */ }
  }, [prefs])

  // Track the OS motion preference live; if the OS turns it on, honour it.
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!mq) return
    const onChange = () => {
      setSystemReduceMotion(mq.matches)
      if (mq.matches) setPrefs((p) => ({ ...p, reduceMotion: true }))
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const setTheme = useCallback((theme: Theme) => setPrefs((p) => ({ ...p, theme })), [])
  const setNightVision = useCallback((nightVision: boolean) => setPrefs((p) => ({ ...p, nightVision })), [])
  const setTextScale = useCallback((textScale: TextScale) => setPrefs((p) => ({ ...p, textScale })), [])
  const setReduceMotion = useCallback((reduceMotion: boolean) => setPrefs((p) => ({ ...p, reduceMotion })), [])
  const cycleTheme = useCallback(() => setPrefs((p) => ({
    ...p, theme: THEME_ORDER[(THEME_ORDER.indexOf(p.theme) + 1) % THEME_ORDER.length],
  })), [])

  const value = useMemo<ThemeContextValue>(() => ({
    ...prefs, setTheme, setNightVision, setTextScale, setReduceMotion, cycleTheme, systemReduceMotion,
  }), [prefs, setTheme, setNightVision, setTextScale, setReduceMotion, cycleTheme, systemReduceMotion])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>')
  return ctx
}

/** Human-readable theme names for the UI. Kept here so labels stay consistent. */
export const THEME_LABELS: Record<Theme, string> = {
  day: 'Day',
  night: 'Night',
  sunlight: 'Sunlight',
}
