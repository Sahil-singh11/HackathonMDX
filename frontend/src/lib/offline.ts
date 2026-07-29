/**
 * Shared connectivity + offline-queue hook.  FROZEN after Phase 0.
 * Used by all three lanes — do not write your own.
 *
 *   const { online, queueLength, syncing, lastSyncError, sync, refresh } = useOffline()
 *
 * Offline is the EXPECTED state for this app, not an error. Present it calmly.
 *
 * This wraps the existing IndexedDB helpers in utils/idb.ts (device queue) and
 * the server-side queue endpoint, and reports one combined count so a page
 * never has to reason about the two separately.
 */
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { listQueue, removeFromQueue } from '../utils/idb'
import { useAppStore } from '../store/app'

export interface OfflineState {
  /** Live connectivity. Seeded from navigator.onLine, kept fresh by events. */
  online: boolean
  /** Device queue + server queue combined. */
  queueLength: number
  /** Device-only queue length, if a page needs the finer detail. */
  deviceQueueLength: number
  syncing: boolean
  lastSyncError: string | null
  /** Flush the device queue to the server, then process the server queue. */
  sync: () => Promise<void>
  /** Re-read queue counts without syncing. */
  refresh: () => Promise<void>
}

export function useOffline(): OfflineState {
  // The app store already tracks online state app-wide; reuse it so the header
  // badge and any page using this hook can never disagree.
  const online = useAppStore((s) => s.online)
  const setOnline = useAppStore((s) => s.setOnline)

  const [deviceQueueLength, setDeviceQueueLength] = useState(0)
  const [serverQueueLength, setServerQueueLength] = useState(0)
  const [syncing, setSyncing] = useState(false)
  const [lastSyncError, setLastSyncError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const local = await listQueue()
      setDeviceQueueLength(local.length)
    } catch {
      setDeviceQueueLength(0) // IndexedDB blocked (private mode) — not fatal.
    }
    try {
      const server = await api.syncQueue()
      setServerQueueLength(server.queued ?? 0)
    } catch {
      setServerQueueLength(0) // Offline is expected; a failed poll is not an error.
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  useEffect(() => {
    const up = () => { setOnline(true); void refresh() }
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => {
      window.removeEventListener('online', up)
      window.removeEventListener('offline', down)
    }
  }, [setOnline, refresh])

  const sync = useCallback(async () => {
    if (!online || syncing) return
    setSyncing(true)
    setLastSyncError(null)
    try {
      for (const item of await listQueue()) {
        await api.createCatch({
          confirmed_species_id: item.species_id,
          measured_length_cm: item.measured_length_cm,
          count: item.count,
          capture_date: item.capture_date,
          fishing_area: item.fishing_area,
        })
        if (item.id != null) await removeFromQueue(item.id)
      }
      await api.processSync()
      await refresh()
    } catch (err) {
      setLastSyncError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }, [online, syncing, refresh])

  return {
    online,
    queueLength: deviceQueueLength + serverQueueLength,
    deviceQueueLength,
    syncing,
    lastSyncError,
    sync,
    refresh,
  }
}
