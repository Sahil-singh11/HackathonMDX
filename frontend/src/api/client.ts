/* Thin API client. The frontend never sees any API key — everything is server-side. */

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
   SHORE-SIDE TYPES (Shirish's lane). Shapes are provisional: no backend
   endpoint exists for these yet, so treat them as a contract to agree on, not
   as something already served.
--------------------------------------------------------------------------- */

export interface SubmissionSummary {
  submission_id: string
  vessel: string
  fisher_name: string
  period_start: string
  period_end: string
  record_count: number
  total_weight_kg: number | null
  status: 'submitted' | 'under_review' | 'verified' | 'flagged'
  submitted_at: string
}

export interface LedgerLink {
  record_id: string
  hash: string
  previous_hash: string | null
}

export interface LedgerVerification {
  intact: boolean
  checked: number
  /** Set only when intact === false: the first record where the chain breaks. */
  broken_at_record_id: string | null
  links: LedgerLink[]
}

export interface CertificateVerification {
  status: 'verified' | 'not_found' | 'chain_broken'
  certificate_ref: string | null
  species_id: string | null
  weight_kg: number | null
  catch_date: string | null
  landing_site: string | null
  vessel: string | null
  ledger_hash: string | null
  /** What this check does and does NOT prove. Render it; do not overclaim. */
  scope_note: string
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
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
 *   Dhanesh  — analyse, catches (listCatches), confirm, createCatch (recordCatch), processSync
 *   Shirish  — getSubmission, listSubmissions, mockSubmit, prepareDeclaration,
 *              submitDeclaration, verifyCertificate, verifyLedger
 */export const api = {
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

  /**
   * TODO(Shirish): no backend route exists yet. Wire this to a real endpoint
   * before rendering anything on /authority — do not fabricate submissions.
   */
  getSubmission(_submissionId: string): Promise<SubmissionSummary> {
    return Promise.reject(new Error('getSubmission: not implemented - no backend endpoint yet'))
  },
  /** TODO(Shirish): as above. */
  listSubmissions(): Promise<{ submissions: SubmissionSummary[] }> {
    return Promise.reject(new Error('listSubmissions: not implemented - no backend endpoint yet'))
  },

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

  /**
   * TODO(Shirish): /verify/:id. There is no certificate or ledger table in the
   * backend yet, so this MUST NOT return an invented "verified" result.
   */
  verifyCertificate(_certificateRef: string): Promise<CertificateVerification> {
    return Promise.reject(new Error('verifyCertificate: not implemented - no ledger/certificate backend yet'))
  },
  /** TODO(Shirish): walks the hash chain. Same caveat as verifyCertificate. */
  verifyLedger(_submissionId: string): Promise<LedgerVerification> {
    return Promise.reject(new Error('verifyLedger: not implemented - no ledger backend yet'))
  },
}
