/**
 * Where the backend lives.
 *
 * Two supported modes, and the ONLY thing that differs between them is this value:
 *
 *   MODE A (recommended)  VITE_API_BASE_URL=https://lamer-konekte.onrender.com
 *                         The teammate runs only the frontend. Hosted Gemma is called by
 *                         the shared backend, so no GEMINI_API_KEY is needed locally.
 *
 *   MODE B (local stack)  VITE_API_BASE_URL unset (or http://127.0.0.1:8000)
 *                         Requests stay relative and Vite's dev proxy forwards /api and
 *                         /health to the local backend. The key lives in the repo-root
 *                         .env and is read by the backend only.
 *
 * Unset is deliberately the default: it keeps same-origin behaviour, which is what the
 * production Docker image needs (FastAPI serves frontend/dist itself, so an absolute URL
 * baked into the bundle would point the deployed app at the wrong host).
 *
 * NO SECRET IS EVER READ HERE. Vite inlines every VITE_* variable into the JavaScript
 * bundle in clear text, so a key placed in a frontend env file would be published to every
 * visitor. The API key is backend-only, by construction — see docs/TEAM_AI_MODEL_SETUP.md.
 */

const RAW = (import.meta.env.VITE_API_BASE_URL ?? '').trim()

/** Normalised base: '' (same origin) or an absolute origin with no trailing slash. */
export const API_BASE = RAW.replace(/\/+$/, '')

/**
 * Absolute URL for a backend path.
 *
 * Paths are passed in already rooted ('/api/...'), so this only prefixes the base. With no
 * base configured the path is returned untouched, which is what keeps the dev proxy and the
 * single-origin production image working.
 */
export function apiUrl(path: string): string {
  if (!API_BASE) return path
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
}

/** True when this build talks to a backend on another origin (Mode A). */
export const IS_REMOTE_BACKEND = API_BASE !== ''
