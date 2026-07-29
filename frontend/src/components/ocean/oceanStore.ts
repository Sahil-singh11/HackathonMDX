/**
 * Shared on/off state for the ambient ocean layer.
 *
 * WHY THIS EXISTS: the previous implementation was a hook with a local
 * useState. Every caller got its OWN copy, so toggling the checkbox in the
 * accessibility panel updated the panel and localStorage but never notified the
 * canvas — its state never changed, its effect never re-ran, and the animation
 * loop kept running. The control looked like it worked and did nothing, while
 * the panel copy promised it saved battery.
 *
 * useSyncExternalStore is the correct primitive here: one value, many
 * subscribers, all re-rendering together. No dependency needed.
 */
import { useSyncExternalStore } from 'react'

const STORAGE_KEY = 'lamer-konekte-ocean'

function readInitial(): boolean {
  try { return localStorage.getItem(STORAGE_KEY) !== 'off' } catch { return true }
}

let enabled = readInitial()
const listeners = new Set<() => void>()

function subscribe(fn: () => void) {
  listeners.add(fn)
  return () => { listeners.delete(fn) }
}

const getSnapshot = () => enabled
/** SSR/prerender safety — the layer is decorative, so default to on. */
const getServerSnapshot = () => true

export function setOceanEnabled(value: boolean) {
  if (enabled === value) return
  enabled = value
  try { localStorage.setItem(STORAGE_KEY, value ? 'on' : 'off') } catch { /* storage blocked */ }
  listeners.forEach((fn) => fn())
}

/** Subscribes to the raw preference. Prefer useOceanState in components. */
export function useOceanPreference(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
