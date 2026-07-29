/* Workstream 2 — OPFS model cache.
 *
 * @litert-lm/core v0.14.0 ships NO caching helper (verified against its .d.ts:
 * the only model input is `EngineSettings.model: string | Blob |
 * ReadableStream<Uint8Array>`). Passing the HTTPS URL straight to Engine.create
 * would re-download ~2 GB on every visit, which is the opposite of what this
 * app is for. So we own the cache: fetch once, persist to OPFS, and hand the
 * engine a Blob from disk thereafter.
 *
 * SIZE WARNING: the web artifact is ~2.0 GB. The master brief's §5 figure of
 * "roughly 1.3 GB" describes the Q4 on-disk weights, NOT the .litertlm web
 * build. Never quote 1.3 GB to a user — see MODEL_BYTES_DOCUMENTED below.
 */

/** Official web artifact — the only E2B build @litert-lm/core accepts. */
export const MODEL_URL =
  'https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/main/gemma-4-E2B-it-web.litertlm'

export const MODEL_FILENAME = 'gemma-4-E2B-it-web.litertlm'

/**
 * Size as published on the Hugging Face repo listing (2.01 GB), used for the
 * consent dialog BEFORE any request is made. The real Content-Length observed
 * at download time always wins once known.
 */
export const MODEL_BYTES_DOCUMENTED = 2_010_000_000

const OPFS_DIR = 'lamer-konekte-models'

export interface DownloadProgress {
  receivedBytes: number
  /** From Content-Length; null when the server does not send one. */
  totalBytes: number | null
}

export interface StorageEstimate {
  quotaBytes: number | null
  usageBytes: number | null
  /** True when the browser reports less headroom than the model needs. */
  insufficient: boolean
}

export function opfsSupported(): boolean {
  return typeof navigator !== 'undefined' && !!navigator.storage?.getDirectory
}

async function modelDir(): Promise<FileSystemDirectoryHandle> {
  const root = await navigator.storage.getDirectory()
  return root.getDirectoryHandle(OPFS_DIR, { create: true })
}

/** Bytes free, and whether that is enough for the model. Never throws. */
export async function estimateStorage(): Promise<StorageEstimate> {
  try {
    const { quota = null, usage = null } = await navigator.storage.estimate()
    const free = quota != null && usage != null ? quota - usage : null
    return {
      quotaBytes: quota,
      usageBytes: usage,
      insufficient: free != null && free < MODEL_BYTES_DOCUMENTED,
    }
  } catch {
    return { quotaBytes: null, usageBytes: null, insufficient: false }
  }
}

/**
 * Ask the browser to make this origin's storage persistent, so the OS does not
 * evict 2 GB under pressure. Best-effort: Chrome grants it silently for
 * installed/engaged origins and refuses otherwise. A refusal is not an error —
 * it only means the cache may be evicted, which we surface to the user.
 */
export async function requestPersistence(): Promise<boolean> {
  try {
    if (await navigator.storage.persisted()) return true
    return await navigator.storage.persist()
  } catch {
    return false
  }
}

/** The cached model file, or null. */
export async function getCachedModel(): Promise<File | null> {
  if (!opfsSupported()) return null
  try {
    const dir = await modelDir()
    const handle = await dir.getFileHandle(MODEL_FILENAME)
    const file = await handle.getFile()
    // A truncated file (interrupted download) is worse than none: the engine
    // would fail deep inside WASM with an unreadable error.
    return file.size > 0 ? file : null
  } catch {
    return null // NotFoundError — simply not cached yet
  }
}

export async function isModelCached(): Promise<boolean> {
  return (await getCachedModel()) != null
}

export async function deleteCachedModel(): Promise<void> {
  if (!opfsSupported()) return
  try {
    const dir = await modelDir()
    await dir.removeEntry(MODEL_FILENAME)
  } catch {
    /* already gone */
  }
}

/**
 * Download the model to OPFS, streaming to disk so a 2 GB file never has to sit
 * in memory. Returns the cached File.
 *
 * Aborting mid-download removes the partial file rather than leaving a
 * corrupt one behind that would look "cached" on the next visit.
 */
export async function downloadModel(
  onProgress: (p: DownloadProgress) => void,
  signal?: AbortSignal,
): Promise<File> {
  if (!opfsSupported()) throw new Error('OPFS is not available in this browser')

  const dir = await modelDir()
  // Write to a temp name, then rename on success, so an interrupted download
  // can never be mistaken for a complete cache entry.
  const tempName = `${MODEL_FILENAME}.partial`
  const handle = await dir.getFileHandle(tempName, { create: true })
  const writable = await handle.createWritable()

  try {
    const res = await fetch(MODEL_URL, { signal })
    if (!res.ok || !res.body) throw new Error(`Model download failed: HTTP ${res.status}`)

    const lenHeader = res.headers.get('content-length')
    const totalBytes = lenHeader ? Number(lenHeader) : null
    let receivedBytes = 0

    const reader = res.body.getReader()
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      await writable.write(value)
      receivedBytes += value.byteLength
      onProgress({ receivedBytes, totalBytes })
    }
    await writable.close()

    // Promote the completed file to its real name.
    const finished = await dir.getFileHandle(tempName)
    const data = await finished.getFile()
    const finalHandle = await dir.getFileHandle(MODEL_FILENAME, { create: true })
    const finalWritable = await finalHandle.createWritable()
    await finalWritable.write(data)
    await finalWritable.close()
    await dir.removeEntry(tempName)

    return await (await dir.getFileHandle(MODEL_FILENAME)).getFile()
  } catch (err) {
    try { await writable.abort() } catch { /* stream already errored */ }
    try { await dir.removeEntry(tempName) } catch { /* nothing to clean */ }
    throw err
  }
}

/** Human-readable size, e.g. "2.0 GB". */
export function formatBytes(bytes: number): string {
  const gb = bytes / 1_000_000_000
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  return `${Math.round(bytes / 1_000_000)} MB`
}
