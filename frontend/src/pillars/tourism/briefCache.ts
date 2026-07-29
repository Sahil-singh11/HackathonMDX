/* Workstream 2 — offline cache for tourism briefs.
 *
 * `lib/offline` (frozen) reports CONNECTIVITY and manages the catch queue; it is
 * not a general-purpose data cache, so extending it would be both out of lane
 * and wrong. This is a tiny separate IndexedDB store for the last brief per
 * query, so a brief stays readable with no signal.
 *
 * The stored copy keeps the provenance block it arrived with, and the surface
 * re-labels it `cached` with its real age on read — a brief that was `live` an
 * hour ago is not live now, and saying otherwise is the exact failure the
 * ProvenanceBadge exists to prevent.
 */

const DB_NAME = 'lamer-konekte-tourism'
const STORE = 'briefs'

export interface CachedBrief<T = unknown> {
  /** Query key: site ids + activity. */
  key: string
  /** When this copy was written to the device. */
  storedAt: string
  payload: T
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) {
        req.result.createObjectStore(STORE, { keyPath: 'key' })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export function briefKey(siteIds: string[], activity: string | null): string {
  return `${[...siteIds].sort().join(',') || 'all'}::${activity ?? 'none'}`
}

export async function putBrief<T>(key: string, payload: T): Promise<void> {
  try {
    const db = await openDb()
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite')
      tx.objectStore(STORE).put({ key, storedAt: new Date().toISOString(), payload })
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch {
    /* IndexedDB blocked (private mode) — caching is best-effort, never fatal. */
  }
}

export async function getBrief<T>(key: string): Promise<CachedBrief<T> | null> {
  try {
    const db = await openDb()
    return await new Promise((resolve, reject) => {
      const req = db.transaction(STORE).objectStore(STORE).get(key)
      req.onsuccess = () => resolve((req.result as CachedBrief<T>) ?? null)
      req.onerror = () => reject(req.error)
    })
  } catch {
    return null
  }
}
