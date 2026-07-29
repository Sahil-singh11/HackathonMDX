/**
 * Shared aria-live region.  FROZEN after Phase 0.
 *
 * One polite live region for the whole app, so async results are announced to
 * a screen reader without every page inventing its own.
 *
 *   <LiveRegion />            // once, in the shell
 *   const announce = useAnnounce()
 *   announce('Catch saved')   // e.g. after analysis completes or a record saves
 *
 * Announce OUTCOMES, not progress spam. "Analysis complete, Day octopus
 * suggested" is useful; "loading… loading…" is noise.
 */
import {
  createContext, useCallback, useContext, useMemo, useRef, useState,
  type ReactNode,
} from 'react'

type Politeness = 'polite' | 'assertive'

interface AnnounceContextValue {
  announce: (message: string, politeness?: Politeness) => void
  politeMessage: string
  assertiveMessage: string
}

const AnnounceContext = createContext<AnnounceContextValue | null>(null)

export function AnnounceProvider({ children }: { children: ReactNode }) {
  const [politeMessage, setPolite] = useState('')
  const [assertiveMessage, setAssertive] = useState('')
  const clearTimer = useRef<number | null>(null)

  const announce = useCallback((message: string, politeness: Politeness = 'polite') => {
    const set = politeness === 'assertive' ? setAssertive : setPolite
    // Clear first so an identical consecutive message still re-announces —
    // screen readers ignore a live region whose text has not changed.
    set('')
    window.requestAnimationFrame(() => set(message))
    if (clearTimer.current) window.clearTimeout(clearTimer.current)
    clearTimer.current = window.setTimeout(() => set(''), 5000)
  }, [])

  const value = useMemo(
    () => ({ announce, politeMessage, assertiveMessage }),
    [announce, politeMessage, assertiveMessage],
  )
  return <AnnounceContext.Provider value={value}>{children}</AnnounceContext.Provider>
}

/** Renders the live regions. Mount once, inside AnnounceProvider. */
export function LiveRegion() {
  const ctx = useContext(AnnounceContext)
  return (
    <>
      <div className="lk-sr-only" role="status" aria-live="polite" aria-atomic="true">
        {ctx?.politeMessage ?? ''}
      </div>
      <div className="lk-sr-only" role="alert" aria-live="assertive" aria-atomic="true">
        {ctx?.assertiveMessage ?? ''}
      </div>
    </>
  )
}

/**
 * Returns announce(). Safe to call outside the provider — it degrades to a
 * no-op rather than throwing, so a lane can use it without worrying about
 * whether the shell mounted the provider on that route.
 */
export function useAnnounce(): (message: string, politeness?: Politeness) => void {
  const ctx = useContext(AnnounceContext)
  return ctx?.announce ?? (() => undefined)
}
