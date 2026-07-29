/* aria-live announcer (Lane B, temporary).
 *
 * The prompt pack expects a shared aria-live helper from Phase 0's lib/. That
 * has not merged, so this is a lane-local stand-in with the same shape:
 * call announce(message) and it is read out politely by screen readers.
 *
 * When Phase 0 lands, delete this file and import the shared helper — the
 * call sites use `announce(string)` and will not need to change.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

export interface Announcer {
  /** Politely announce a message to assistive technology. */
  announce: (message: string) => void
  /** Render this once per page, anywhere. */
  LiveRegion: () => JSX.Element
}

export function useAnnounce(): Announcer {
  const [message, setMessage] = useState('')
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => window.clearTimeout(timer.current), [])

  const announce = useCallback((next: string) => {
    // Clear first so repeating the same string still triggers an announcement.
    setMessage('')
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setMessage(next), 60)
  }, [])

  const LiveRegion = useCallback(
    () => <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{message}</div>,
    [message],
  )

  return { announce, LiveRegion }
}
