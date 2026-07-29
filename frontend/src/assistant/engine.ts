/* Workstream 2 — browser inference engine lifecycle.
 *
 * Wraps @litert-lm/core v0.14.0. API verified against the shipped .d.ts, not
 * the docs page:
 *   Engine.create({ model: string | Blob | ReadableStream }): Promise<Engine>
 *   engine.createConversation(config?): Promise<Conversation>
 *   conversation.sendMessageStreaming(msg): ReadableStream<Message>
 *   conversation.cancel(): void
 *
 * KNOWN UNVERIFIED: no one has yet run a token through this on real hardware.
 * The download, cache, capability-detection and decline paths below are
 * testable without a model; actual generation is not, and must not be claimed
 * as working until someone demonstrates it in a WebGPU browser.
 */
import type { Conversation, Engine } from '@litert-lm/core'

export type EngineStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface Capability {
  webgpu: boolean
  opfs: boolean
  /** Cross-origin isolation — required for SharedArrayBuffer in some builds. */
  crossOriginIsolated: boolean
  supported: boolean
  reason: 'ok' | 'no-webgpu' | 'no-opfs'
}

/**
 * Feature-detect before offering a 2 GB download. Checking `navigator.gpu`
 * alone is not enough — the property exists in browsers that cannot actually
 * grant an adapter — so we request one.
 */
export async function detectCapability(): Promise<Capability> {
  const opfs = typeof navigator !== 'undefined' && !!navigator.storage?.getDirectory
  let webgpu = false
  try {
    const gpu = (navigator as Navigator & { gpu?: { requestAdapter(): Promise<unknown> } }).gpu
    if (gpu) webgpu = (await gpu.requestAdapter()) != null
  } catch {
    webgpu = false
  }
  const reason: Capability['reason'] = !webgpu ? 'no-webgpu' : !opfs ? 'no-opfs' : 'ok'
  return {
    webgpu,
    opfs,
    crossOriginIsolated: typeof globalThis !== 'undefined' && !!globalThis.crossOriginIsolated,
    supported: webgpu && opfs,
    reason,
  }
}

/**
 * Where the WASM runtime is served from — OUR origin, never a CDN.
 *
 * @litert-lm/core would otherwise fetch it from cdn.jsdelivr.net, which fails
 * exactly when a fisher has no signal. vite.config.ts copies the runtime here
 * at build time and serves it from node_modules in dev.
 */
export const WASM_PATH = '/litert-wasm'

let capabilityPromise: Promise<Capability> | null = null

/** detectCapability memoised — requestAdapter() is not free, and the answer
 *  cannot change within a page load. */
export function detectCapabilityCached(): Promise<Capability> {
  if (!capabilityPromise) capabilityPromise = detectCapability()
  return capabilityPromise
}

let enginePromise: Promise<Engine> | null = null

/**
 * Create (once) the engine from a cached model Blob.
 *
 * The import is dynamic so the WASM runtime is never pulled into the main
 * bundle — a fisher who only ever uses the rules browser must not pay for it.
 */
export async function getEngine(model: Blob): Promise<Engine> {
  if (!enginePromise) {
    enginePromise = (async () => {
      const { Engine: EngineCtor, getOrLoadGlobalLiteRtLm } = await import('@litert-lm/core')
      // Load the runtime from our own origin BEFORE Engine.create, which would
      // otherwise lazily pull it from the jsdelivr CDN.
      await getOrLoadGlobalLiteRtLm(WASM_PATH)
      return EngineCtor.create({ model })
    })()
    // A failed load must not poison every later attempt.
    enginePromise.catch(() => { enginePromise = null })
  }
  return enginePromise
}

export async function disposeEngine(): Promise<void> {
  const p = enginePromise
  enginePromise = null
  if (!p) return
  try {
    const engine = await p
    await engine.delete()
  } catch {
    /* already gone */
  }
}

/** Extract plain text from a Message, whose content is string | ContentPart[]. */
export function messageText(message: { content?: unknown }): string {
  const { content } = message
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .map((part) => (part && typeof part === 'object' && 'text' in part
        ? String((part as { text: unknown }).text ?? '') : ''))
      .join('')
  }
  return ''
}

/**
 * Stream a reply, invoking onToken with each incremental chunk.
 *
 * sendMessageStreaming returns a ReadableStream (not an async iterable), so we
 * read it explicitly — async iteration over ReadableStream is not available in
 * every browser this app targets.
 */
export async function streamReply(
  conversation: Conversation,
  message: string,
  onToken: (text: string) => void,
): Promise<string> {
  const stream = conversation.sendMessageStreaming(message)
  const reader = stream.getReader()
  let full = ''
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      const text = messageText(value as { content?: unknown })
      if (text) { full += text; onToken(text) }
    }
  } finally {
    reader.releaseLock()
  }
  return full
}
