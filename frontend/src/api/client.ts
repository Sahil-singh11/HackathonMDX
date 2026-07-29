/* Thin API client. The frontend never sees any API key — everything is server-side. */
import { RateLimitError, emitRateLimited } from '../lib/httpError'

export interface PublicConfig {
  app: string
  tagline: string
  provider_mode_default: string
  hosted_configured: boolean
  model: string | null
  current_date: string
  date_simulated: boolean
  limitation: string
  marine_disclaimer: string
}

export interface SpeciesCandidate {
  species_id: string
  scientific: string
  english: string
  morisyen: string
  morisyen_status: string
  visible_characteristics: string[]
}

export interface AnalyseResponse {
  analysis_id: string
  intent: string
  image_quality: { status: 'acceptable' | 'poor' | 'invalid'; blur_score: number; brightness: number; warnings: string[] }
  species_suggestion: { species_id: string | null; morisyen: string | null; english: string | null; scientific: string | null }
  visible_characteristics: string[]
  confidence_label: 'low' | 'medium' | 'high'
  species_confirmation_required: boolean
  estimated_size_unverified_cm: number | null
  measured_size_required: boolean
  legal_check: LegalCheck
  reply: string
  reply_morisyen: string
  recommended_next_step: string
  function_trace: import('../store/app').FunctionTraceEntry[]
  provider: import('../store/app').ProviderInfo
  limitations: string[]
}

export interface LegalCheck {
  status: string
  rule: string | null
  source_id: string | null
  verification_status?: string | null
  note?: string | null
}

export interface ConfirmResponse {
  catch_record_id: string
  species_id: string
  legal_check: LegalCheck
  measured_length_cm: number | null
  count: number
  capture_date: string
  limitations: string[]
}

/* ---------------------------------------------------------------------------
   SHORE-SIDE TYPES (Shirish's lane).
   These now mirror REAL endpoints added in the traceability-ledger commit:
   /api/ledger, /api/ledger/verify, /api/verify/{record_id}, /api/submissions,
   /api/submissions/{declaration_id}.

   Every one of them returns a scope_note. RENDER IT. The chain proves a record
   is unaltered since it was logged; it does not prove the reported catch
   details are true, and it is a local chain, not a distributed blockchain.
--------------------------------------------------------------------------- */

export interface SubmissionSummary {
  declaration_id: string
  fisher_name: string
  fishing_area: string
  period_start: string
  period_end: string
  record_count: number
  total_count: number
  status: string
  mock_receipt_id: string | null
  submitted_at: string
}

export interface LedgerEntry {
  seq: number
  record_id: string
  payload_sha256: string
  prev_hash: string
  entry_hash: string
  created_at: string
}

export interface LedgerChain {
  entries: LedgerEntry[]
  genesis_hash: string
  count: number
  scope_note: string
}

export interface LedgerVerification {
  /** 'empty' is returned before any catch has been sealed — design a real state
   *  for it rather than letting it fall through to a scary "broken". */
  status: 'intact' | 'broken' | 'empty'
  entries: number
  verified_through: number
  /** Names the FIRST record where the chain breaks; null when intact. */
  broken_at: string | null
  detail: string
  scope_note: string
}

/** Public QR-landing verification. Three verdicts, never more confident. */
export interface CertificateVerification {
  status: 'verified' | 'not_found' | 'chain_broken'
  scope_note: string
  [key: string]: unknown
}

/**
 * The regulatory dataset served verbatim by GET /api/rules/static
 * (Workstream 2). The offline assistant bundles the same JSON at build time and
 * calls this only to detect a stale bundle, so `rules_version` is the field
 * that matters; the payloads are typed loosely on purpose because the assistant
 * narrows them in `assistant/rulesData.ts` rather than duplicating shapes here.
 */
export interface StaticRules {
  rules_version: string
  rules: Record<string, unknown>
  catalogue: Record<string, unknown>
  sources: Record<string, unknown>
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (res.status === 429) {
    // /api/analyse-catch is throttled at 10 req/min per address (backend/app/core/ratelimit.py);
    // /api/demo/reset clears it. Every caller gets this uniformly — nobody needs
    // to special-case 429 in their own page.
    const seconds = Number(res.headers.get('Retry-After')) || 60
    emitRateLimited(seconds)
    throw new RateLimitError(seconds)
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<T>
}

/**
 * API client.
 *
 * MERGE RULE: keep these functions in ALPHABETICAL ORDER and fill in only the
 * bodies you own. Alphabetical ordering keeps three developers' diffs from
 * landing adjacent to each other.
 *
 * Ownership:
 *   Sahil    — config, marine, providerStatus, reportToday, species, syncQueue
 *   Dhanesh  — analyse, catches (listCatches), confirm, createCatch (recordCatch),
 *              processSync, rulesStatic
 *   Shirish  — getSubmission, listSubmissions, mockSubmit, prepareDeclaration,
 *              submitDeclaration, verifyCertificate, verifyLedger
 */
export const api = {
  analyse(form: FormData): Promise<AnalyseResponse> {
    return fetch('/api/analyse-catch', { method: 'POST', body: form }).then((r) => jsonOrThrow<AnalyseResponse>(r))
  },
  catches: () => fetch('/api/catches').then((r) => jsonOrThrow<{ catches: Record<string, unknown>[] }>(r)),
  config: () => fetch('/api/config/public').then((r) => jsonOrThrow<PublicConfig>(r)),
  confirm(analysisId: string, body: Record<string, unknown>): Promise<ConfirmResponse> {
    return fetch(`/api/analyses/${analysisId}/confirm`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then((r) => jsonOrThrow<ConfirmResponse>(r))
  },
  createCatch(body: Record<string, unknown>): Promise<ConfirmResponse> {
    return fetch('/api/catches', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then((r) => jsonOrThrow<ConfirmResponse>(r))
  },
  demoReset: () => fetch('/api/demo/reset', { method: 'POST' }).then((r) => jsonOrThrow<Record<string, unknown>>(r)),

  getSubmission: (declarationId: string) =>
    fetch(`/api/submissions/${declarationId}`).then((r) => jsonOrThrow<Record<string, unknown>>(r)),

  /** Officer view. Walks the whole hash chain; use for the ledger inspector. */
  ledger: (limit = 200) =>
    fetch(`/api/ledger?limit=${limit}`).then((r) => jsonOrThrow<LedgerChain>(r)),

  listSubmissions: () =>
    fetch('/api/submissions').then((r) => jsonOrThrow<{ submissions: SubmissionSummary[]; count: number; mock_label: string }>(r)),

  marine: () => fetch('/api/marine-conditions').then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  mockSubmit(declarationId: string) {
    const form = new FormData()
    form.append('declaration_id', declarationId)
    return fetch('/api/declarations/mock-submit', { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  prepareDeclaration(data: Record<string, string>) {
    const form = new FormData()
    Object.entries(data).forEach(([k, v]) => form.append(k, v))
    return fetch('/api/declarations/prepare', { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  processSync: () => fetch('/api/sync/process', { method: 'POST' }).then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  providerStatus: () => fetch('/api/provider/status').then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  reportToday: () => fetch('/api/reports/today').then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  rulesStatic: () => fetch('/api/rules/static').then((r) => jsonOrThrow<StaticRules>(r)),
  setDemoDate(date: string) {
    const form = new FormData()
    form.append('simulated_date', date)
    return fetch('/api/demo/set-date', { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  species: () => fetch('/api/species').then((r) => jsonOrThrow<{ species: SpeciesCandidate[] }>(r)),

  /**
   * TODO(Shirish): named slot for the /declaration rebuild. Currently delegates
   * to the existing mock-submit route so the contract is visible without
   * pretending a new backend exists.
   */
  submitDeclaration(declarationId: string): Promise<Record<string, unknown>> {
    return api.mockSubmit(declarationId)
  },

  syncQueue: () => fetch('/api/sync/queue').then((r) => jsonOrThrow<{ items: Record<string, unknown>[]; queued: number }>(r)),

  /** Public, no auth. Backs /verify/:id. Render status AND scope_note. */
  verifyCertificate: (recordId: string) =>
    fetch(`/api/verify/${recordId}`).then((r) => jsonOrThrow<CertificateVerification>(r)),

  /** Chain integrity. Reports the FIRST broken record, or intact. */
  verifyLedger: () =>
    fetch('/api/ledger/verify').then((r) => jsonOrThrow<LedgerVerification>(r)),
}
