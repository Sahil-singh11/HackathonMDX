import react from '@vitejs/plugin-react'
import { cpSync, existsSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { defineConfig, type Plugin } from 'vite'

const require = createRequire(import.meta.url)

/**
 * Self-host the LiteRT-LM WASM runtime (Workstream 2).
 *
 * @litert-lm/core defaults to loading its runtime from
 * `https://cdn.jsdelivr.net/npm/@litert-lm/core@<v>/wasm`. That breaks the
 * app's core promise the same way a CDN font would (CLAUDE.md: "this app must
 * work with no signal, which is exactly when a CDN fetch fails") — and it is
 * worse here, because the offline assistant would fetch ~20-31 MB from a third
 * party at the moment the fisher has no connection.
 *
 * So we copy the runtime into the build and point the loader at our own origin
 * (see assistant/engine.ts WASM_PATH). The directory holds four variants; the
 * loader picks one by feature detection, so all of them must be present.
 *
 * The files are NOT committed — they are copied from node_modules at build
 * time, and `/litert-wasm` is gitignored.
 */
function selfHostLiteRtWasm(): Plugin {
  const wasmSrc = join(dirname(require.resolve('@litert-lm/core/package.json')), 'wasm')
  return {
    name: 'lamer-konekte:self-host-litert-wasm',
    apply: () => true,
    configureServer(server) {
      // Dev: serve the runtime straight out of node_modules.
      server.middlewares.use('/litert-wasm', (req, res, next) => {
        const name = (req.url ?? '').split('?')[0].replace(/^\//, '')
        const file = join(wasmSrc, name)
        if (!name || !existsSync(file)) return next()
        res.setHeader('Content-Type', name.endsWith('.wasm') ? 'application/wasm' : 'text/javascript')
        require('node:fs').createReadStream(file).pipe(res)
      })
    },
    closeBundle() {
      // Build: copy into dist so the deployed origin serves it.
      if (existsSync(wasmSrc)) cpSync(wasmSrc, join('dist', 'litert-wasm'), { recursive: true })
    },
  }
}

export default defineConfig({
  plugins: [react(), selfHostLiteRtWasm()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
  build: { sourcemap: false },
})
