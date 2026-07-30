/* Thin API client. The frontend never sees any API key — everything is server-side. */
import { RateLimitError, emitRateLimited } from '../lib/httpError'
import { apiUrl } from './base'
import type { PillarProbe, PillarResult, PillarsResponse } from '../pillars/types'
import type { ArrivalsBrief } from '../pillars/transport/types'

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

/** Manual AI test console result. A narrow, safe projection of the production
 *  pipeline — deliberately carries no argument values, no prompt, no reasoning. */
export interface ConsoleResult {
  final_response: string
  reply_morisyen: string
  intent: string
  provider: string
  model: string
  real_inference: boolean
  latency_ms: number
  selected_function: string | null
  functions_called: string[]
  argument_names: string[]
  tool_round_trip_completed: boolean
  schema_valid: boolean
  safety_flags: Record<string, boolean>
  mock_used: boolean
  mock_label: string
  disclosures: string[]
  function_trace: import('../store/app').FunctionTraceEntry[]
  controlled_error: { kind: 'transient' | 'behavioural'; message: string } | null
}

/** One turn of the conversational assistant. `role` mirrors the backend enum. */
export interface ChatTurn {
  role: 'user' | 'assistant'
  text: string
}

/**
 * A reply from POST /api/ai/chat.
 *
 * `real_inference` and `grounded_only` are the two fields that must never be
 * hidden. When Gemma cannot be reached the backend still answers — from the
 * rules files, deterministically — and the fisher is entitled to know which of
 * the two they are reading. `cited_rules` are ids they can look up in the
 * Fishing rules page.
 */
export interface ChatResult {
  reply: string
  provider: string
  model: string
  real_inference: boolean
  latency_ms: number
  functions_called: string[]
  function_trace: import('../store/app').FunctionTraceEntry[]
  cited_rules: string[]
  disclosures: string[]
  grounded_only: boolean
  grounded_label: string
  controlled_error: { kind: 'transient' | 'behavioural'; message: string } | null
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

/* ---------------------------------------------------------------------------
   BLUE FINANCE PILLAR (Task 6b, Shirish's lane). Mirrors
   backend/app/pillars/finance/schemas.py exactly — see pillars/types.ts's own
   note on why these are kept in sync by hand rather than generated.
--------------------------------------------------------------------------- */

export interface FinanceSample {
  sample_id: string
  filename: string
  label: string
}

export interface FinanceExtractedField {
  field: string
  value: string | null
  page: number | null
  span: string | null
  supported: boolean
  unsupported_reason: string
}

/** Never a verdict on the bond — `status` is per-criterion only. */
export interface FinanceCriteriaFinding {
  criterion_id: string
  label: string
  status: 'met' | 'unmet' | 'indeterminate'
  evidence: FinanceExtractedField[]
  note: string
  advisory_only: boolean
}

export interface FinanceResult extends PillarResult {
  document_label: string
  fields: FinanceExtractedField[]
  findings: FinanceCriteriaFinding[]
  overall_note: string
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
 *              energyResource, pillarProvenance, pillars, processSync, rulesStatic,
 *              tourismBrief, tourismSites
 *   Shirish  — financeAnalyse, financeCriteria, financeSamples, getSubmission,
 *              listSubmissions, mockSubmit, prepareDeclaration,
 *              submitDeclaration, verifyCertificate, verifyLedger
 */
export const api = {
  /** Conversational assistant. Send the whole visible conversation (oldest first, last
   *  turn from the fisher); the backend re-grounds every turn against the rules data and
   *  answers deterministically from it when hosted Gemma is unreachable. */
  aiChat(messages: ChatTurn[], language: 'en' | 'mfe'): Promise<ChatResult> {
    return fetch(apiUrl('/api/ai/chat'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, language }),
    }).then((r) => jsonOrThrow<ChatResult>(r))
  },

  /** Manual AI test console (Technical Proof page). Runs one free-text prompt through the
   *  SAME production inference path as `analyse` and returns only safe metadata — no key,
   *  no prompt text, no reasoning, argument names only. */
  aiTestConsole(prompt: string, language: 'en' | 'mfe'): Promise<ConsoleResult> {
    return fetch(apiUrl('/api/ai/test-console'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, language }),
    }).then((r) => jsonOrThrow<ConsoleResult>(r))
  },
  analyse(form: FormData): Promise<AnalyseResponse> {
    return fetch(apiUrl('/api/analyse-catch'), { method: 'POST', body: form }).then((r) => jsonOrThrow<AnalyseResponse>(r))
  },
  catches: () => fetch(apiUrl('/api/catches')).then((r) => jsonOrThrow<{ catches: Record<string, unknown>[] }>(r)),
  config: () => fetch(apiUrl('/api/config/public')).then((r) => jsonOrThrow<PublicConfig>(r)),
  confirm(analysisId: string, body: Record<string, unknown>): Promise<ConfirmResponse> {
    return fetch(apiUrl(`/api/analyses/${analysisId}/confirm`), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then((r) => jsonOrThrow<ConfirmResponse>(r))
  },
  createCatch(body: Record<string, unknown>): Promise<ConfirmResponse> {
    return fetch(apiUrl('/api/catches'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then((r) => jsonOrThrow<ConfirmResponse>(r))
  },
  demoReset: () => fetch(apiUrl('/api/demo/reset'), { method: 'POST' }).then((r) => jsonOrThrow<Record<string, unknown>>(r)),

  /** Wave/wind resource indication. Figures are computed server-side in Python. */
  energyResource: (siteIds?: string[]) => {
    const qs = siteIds?.length ? `?site_ids=${siteIds.join(',')}` : ''
    return fetch(apiUrl(`/api/pillars/energy/resource${qs}`))
      .then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },

  /** Runs the deterministic criteria check against a sample or an uploaded PDF.
   *  503 while the pillar is disabled — the panel must render that state, not hide it. */
  financeAnalyse(params: { sampleId?: string; file?: File }): Promise<FinanceResult> {
    const form = new FormData()
    if (params.sampleId) form.append('sample_id', params.sampleId)
    if (params.file) form.append('document', params.file)
    return fetch(apiUrl('/api/pillars/finance/analyse'), { method: 'POST', body: form })
      .then((r) => jsonOrThrow<FinanceResult>(r))
  },
  financeCriteria: () =>
    fetch(apiUrl('/api/pillars/finance/criteria')).then((r) => jsonOrThrow<{ criteria: Record<string, unknown>[] }>(r)),
  financeSamples: () =>
    fetch(apiUrl('/api/pillars/finance/samples')).then((r) => jsonOrThrow<{ samples: FinanceSample[] }>(r)),

  getSubmission: (declarationId: string) =>
    fetch(apiUrl(`/api/submissions/${declarationId}`)).then((r) => jsonOrThrow<Record<string, unknown>>(r)),

  /** Officer view. Walks the whole hash chain; use for the ledger inspector. */
  ledger: (limit = 200) =>
    fetch(apiUrl(`/api/ledger?limit=${limit}`)).then((r) => jsonOrThrow<LedgerChain>(r)),

  listSubmissions: () =>
    fetch(apiUrl('/api/submissions')).then((r) => jsonOrThrow<{ submissions: SubmissionSummary[]; count: number; mock_label: string }>(r)),

  marine: () => fetch(apiUrl('/api/marine-conditions')).then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  mockSubmit(declarationId: string) {
    const form = new FormData()
    form.append('declaration_id', declarationId)
    return fetch(apiUrl('/api/declarations/mock-submit'), { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  /**
   * Cheap data-source probe for one pillar (fetch() only, no inference).
   * Returns 404 for pillars that do not implement the optional /provenance
   * convention — callers must render that absence, never guess a data_kind.
   */
  pillarProvenance: (pillarId: string) =>
    fetch(apiUrl(`/api/pillars/${pillarId}/provenance`)).then((r) => jsonOrThrow<PillarProbe>(r)),

  /** All six blue-economy pillars with their real registry state (Task 4a). */
  pillars: () => fetch(apiUrl('/api/pillars')).then((r) => jsonOrThrow<PillarsResponse>(r)),

  prepareDeclaration(data: Record<string, string>) {
    const form = new FormData()
    Object.entries(data).forEach(([k, v]) => form.append(k, v))
    return fetch(apiUrl('/api/declarations/prepare'), { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  processSync: () => fetch(apiUrl('/api/sync/process'), { method: 'POST' }).then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  providerStatus: () => fetch(apiUrl('/api/provider/status')).then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  reportToday: () => fetch(apiUrl('/api/reports/today')).then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  rulesStatic: () => fetch(apiUrl('/api/rules/static')).then((r) => jsonOrThrow<StaticRules>(r)),
  setDemoDate(date: string) {
    const form = new FormData()
    form.append('simulated_date', date)
    return fetch(apiUrl('/api/demo/set-date'), { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  species: () => fetch(apiUrl('/api/species')).then((r) => jsonOrThrow<{ species: SpeciesCandidate[] }>(r)),

  /**
   * TODO(Shirish): named slot for the /declaration rebuild. Currently delegates
   * to the existing mock-submit route so the contract is visible without
   * pretending a new backend exists.
   */
  submitDeclaration(declarationId: string): Promise<Record<string, unknown>> {
    return api.mockSubmit(declarationId)
  },

  syncQueue: () => fetch(apiUrl('/api/sync/queue')).then((r) => jsonOrThrow<{ items: Record<string, unknown>[]; queued: number }>(r)),

  /** Public, no auth. Backs /verify/:id. Render status AND scope_note. */
  /** Condition briefs. `activity` ranks sites on FORECAST CONDITIONS only. */
  tourismBrief: (params: { siteIds?: string[]; activity?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.siteIds?.length) q.set('site_ids', params.siteIds.join(','))
    if (params.activity) q.set('activity', params.activity)
    const qs = q.toString()
    return fetch(apiUrl(`/api/pillars/tourism/brief${qs ? `?${qs}` : ''}`))
      .then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  tourismSites: () =>
    fetch(apiUrl('/api/pillars/tourism/sites')).then((r) => jsonOrThrow<Record<string, unknown>>(r)),

  /**
   * Port Louis arrivals brief. Counts, ETAs and ordering are deterministic;
   * `narrative` / `risk_reasoning` are model prose ABOUT those numbers and are
   * never parsed back into data — read `narrative_source` to know which of the
   * two actually served, and render that distinction.
   *
   * Can legitimately take up to ~60 s: the narrative step waits on hosted
   * Gemma before the backend falls back. Callers should not retry on timeout.
   */
  transportArrivals: () =>
    fetch(apiUrl('/api/pillars/transport/arrivals')).then((r) => jsonOrThrow<ArrivalsBrief>(r)),

  verifyCertificate: (recordId: string) =>
    fetch(apiUrl(`/api/verify/${recordId}`)).then((r) => jsonOrThrow<CertificateVerification>(r)),

  /** Chain integrity. Reports the FIRST broken record, or intact. */
  verifyLedger: () =>
    fetch(apiUrl('/api/ledger/verify')).then((r) => jsonOrThrow<LedgerVerification>(r)),
}
