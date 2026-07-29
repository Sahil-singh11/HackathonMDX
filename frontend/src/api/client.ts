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

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  config: () => fetch('/api/config/public').then((r) => jsonOrThrow<PublicConfig>(r)),
  providerStatus: () => fetch('/api/provider/status').then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  species: () => fetch('/api/species').then((r) => jsonOrThrow<{ species: SpeciesCandidate[] }>(r)),
  marine: () => fetch('/api/marine-conditions').then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  catches: () => fetch('/api/catches').then((r) => jsonOrThrow<{ catches: Record<string, unknown>[] }>(r)),
  reportToday: () => fetch('/api/reports/today').then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  syncQueue: () => fetch('/api/sync/queue').then((r) => jsonOrThrow<{ items: Record<string, unknown>[]; queued: number }>(r)),

  analyse(form: FormData): Promise<AnalyseResponse> {
    return fetch('/api/analyse-catch', { method: 'POST', body: form }).then((r) => jsonOrThrow<AnalyseResponse>(r))
  },
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
  prepareDeclaration(data: Record<string, string>) {
    const form = new FormData()
    Object.entries(data).forEach(([k, v]) => form.append(k, v))
    return fetch('/api/declarations/prepare', { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  mockSubmit(declarationId: string) {
    const form = new FormData()
    form.append('declaration_id', declarationId)
    return fetch('/api/declarations/mock-submit', { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  setDemoDate(date: string) {
    const form = new FormData()
    form.append('simulated_date', date)
    return fetch('/api/demo/set-date', { method: 'POST', body: form }).then((r) => jsonOrThrow<Record<string, unknown>>(r))
  },
  demoReset: () => fetch('/api/demo/reset', { method: 'POST' }).then((r) => jsonOrThrow<Record<string, unknown>>(r)),
  processSync: () => fetch('/api/sync/process', { method: 'POST' }).then((r) => jsonOrThrow<Record<string, unknown>>(r)),
}
