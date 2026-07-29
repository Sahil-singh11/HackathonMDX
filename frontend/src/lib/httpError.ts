/**
 * 429 interceptor for the shared fetch layer.
 *
 * api/client.ts's jsonOrThrow() is the ONE place every lane's api.* call
 * already passes through, so it is the natural interception point for a
 * cross-cutting concern like throttling — this module adds a typed error and
 * a tiny pub/sub there instead of editing any individual api.* function body
 * or any page. RateLimitBanner (components/http) is the only subscriber, and
 * mounts once at the app root, so no page needs to know a limiter exists.
 */

export class RateLimitError extends Error {
  constructor(public retryAfterSeconds: number) {
    super(`Rate limited — retry after ${retryAfterSeconds}s`)
    this.name = 'RateLimitError'
  }
}

type RateLimitListener = (retryAfterSeconds: number) => void

const listeners = new Set<RateLimitListener>()

/** Subscribe to 429 events. Returns an unsubscribe function. */
export function onRateLimited(fn: RateLimitListener): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function emitRateLimited(retryAfterSeconds: number): void {
  listeners.forEach((fn) => fn(retryAfterSeconds))
}
