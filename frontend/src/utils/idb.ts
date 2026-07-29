/* Tiny IndexedDB queue for offline catch records. */
const DB_NAME = 'lamer-konekte'
const STORE = 'offline-queue'

export interface QueuedCatch {
  id?: number
  species_id: string
  measured_length_cm: number | null
  count: number
  capture_date: string
  fishing_area: string
  queued_at: string
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) {
        req.result.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function enqueue(item: Omit<QueuedCatch, 'id'>): Promise<void> {
  const db = await openDb()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).add(item)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function listQueue(): Promise<QueuedCatch[]> {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const req = db.transaction(STORE).objectStore(STORE).getAll()
    req.onsuccess = () => resolve(req.result as QueuedCatch[])
    req.onerror = () => reject(req.error)
  })
}

export async function removeFromQueue(id: number): Promise<void> {
  const db = await openDb()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).delete(id)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}
