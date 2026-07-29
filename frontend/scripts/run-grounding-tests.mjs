/* Workstream 2 — run the grounding tests without adding a test-runner dependency.
 *
 * esbuild already ships as a Vite dependency, so this bundles the TS (including
 * the JSON imports) to a temp file and runs it in Node. No new package, no
 * change to the shared build scripts.
 *
 *   node scripts/run-grounding-tests.mjs
 */
import { build } from 'esbuild'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const outDir = mkdtempSync(join(tmpdir(), 'lk-grounding-'))
const outfile = join(outDir, 'grounding.test.mjs')

try {
  await build({
    entryPoints: ['src/assistant/grounding.test.ts'],
    outfile,
    bundle: true,
    platform: 'node',
    format: 'esm',
    loader: { '.json': 'json' },
    logLevel: 'warning',
  })
  await import(pathToFileURL(outfile).href)
} finally {
  rmSync(outDir, { recursive: true, force: true })
}
