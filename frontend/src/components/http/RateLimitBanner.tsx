/**
 * App-wide notice for the analyse-catch throttle (10 req/min per address,
 * backend/app/core/ratelimit.py; /api/demo/reset clears it).
 *
 * Mounted once at the app root (main.tsx) and driven by lib/httpError's
 * pub/sub, so it appears no matter which page triggered the 429 — no page
 * needs to import or know about it. Never shows raw "HTTP 429" text.
 *
 * Ticks down live, once a second, then flips to a "you can try again" state
 * instead of just disappearing — a fisher (or a judge) should not have to
 * guess whether the cool-down is over.
 */
import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, X } from 'lucide-react'
import { onRateLimited } from '../../lib/httpError'
import { useAnnounce } from '../../lib/announce'
import { useT } from '../../i18n'
import './rateLimit.css'

export function RateLimitBanner() {
  const t = useT()
  const announce = useAnnounce()
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null)
  const announcedReadyRef = useRef(false)

  useEffect(() => onRateLimited((seconds) => {
    announcedReadyRef.current = false
    setSecondsLeft(Math.max(1, Math.round(seconds)))
    announce(t('httpError.rateLimited').replace('{seconds}', String(Math.round(seconds))), 'assertive')
  }), [announce, t])

  useEffect(() => {
    if (secondsLeft === null) return
    if (secondsLeft <= 0) {
      if (!announcedReadyRef.current) {
        announcedReadyRef.current = true
        announce(t('httpError.rateLimitedReady'), 'polite')
      }
      return
    }
    const id = window.setTimeout(() => setSecondsLeft((s) => (s ?? 1) - 1), 1000)
    return () => window.clearTimeout(id)
  }, [secondsLeft, announce, t])

  if (secondsLeft === null) return null
  const ready = secondsLeft <= 0

  return (
    <div className="lk-scope lk-ratelimit-region" role="status">
      <div className={`lk-ratelimit${ready ? ' lk-ratelimit--ready' : ''}`}>
        {ready ? <CheckCircle2 size={20} aria-hidden="true" /> : <AlertTriangle size={20} aria-hidden="true" />}
        <span className="lk-ratelimit__body">
          {ready ? t('httpError.rateLimitedReady') : t('httpError.rateLimited').replace('{seconds}', String(secondsLeft))}
        </span>
        <button type="button" className="lk-ratelimit__dismiss" onClick={() => setSecondsLeft(null)} aria-label="Dismiss">
          <X size={18} aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
