/* Workstream 2 — /pillars index (5a shell, 5d demo entry point).
 *
 * Lists all six national pillars with their real registry state, and — the 5d
 * job — shows each one's data_kind at a glance, so the first thing a viewer
 * learns is which pillars run on live data and which run on samples.
 *
 * HOW data_kind IS OBTAINED, and why it is not free: data_kind lives on a
 * PillarResult's provenance, not on the descriptor /api/pillars returns. Asking
 * each pillar for a full result would work but costs model calls — measured at
 * over 120 s for tourism and energy on 2026-07-30. So each pillar may expose a
 * cheap `/provenance` probe (fetch() only, ~10-30 ms). Pillars that have not
 * adopted it return 404 and render as "not reported" — an absence, never a
 * guessed label.
 *
 * Live/registered comes from the backend's own derived state (implemented AND
 * opted in via PILLARS_ENABLED). We never infer it: a pillar that has merged but
 * is not enabled reads as "registered", because 503 is what a caller would get.
 */
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, CircleDot, HelpCircle, Layers } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { Badge, Card, Skeleton } from '../components/ui'
import { useT } from '../i18n'
import ProvenanceBadge from './ProvenanceBadge'
import { BADGE_EXAMPLES, FIXTURE_PILLARS } from './fixture'
import './pillars.css'
import type { DataKind, PillarDescriptor, PillarProbe } from './types'

export function PillarStatusBadge({ pillar }: { pillar: PillarDescriptor }) {
  const t = useT()
  return pillar.status === 'live'
    ? <Badge tone="success" icon={<CircleDot size={14} aria-hidden="true" />}>{t('pillars.status.live')}</Badge>
    : <Badge tone="neutral">{t('pillars.status.registered')}</Badge>
}

/** Probe every live pillar in parallel; a rejection means "not reported". */
async function probeAll(pillars: PillarDescriptor[]): Promise<Record<string, PillarProbe>> {
  const live = pillars.filter((p) => p.status === 'live')
  const settled = await Promise.allSettled(live.map((p) => api.pillarProvenance(p.pillar_id)))
  const out: Record<string, PillarProbe> = {}
  settled.forEach((res, i) => {
    if (res.status === 'fulfilled') out[live[i].pillar_id] = res.value
  })
  return out
}

const KIND_TONE: Record<DataKind, 'success' | 'neutral' | 'warning' | 'danger'> = {
  live: 'success', cached: 'neutral', sample: 'warning', synthetic: 'danger',
}

export default function PillarsIndex() {
  const t = useT()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['pillars'],
    queryFn: api.pillars,
    retry: 1,
  })

  const usingFixture = isError || !data
  const pillars = data?.pillars ?? FIXTURE_PILLARS
  // The API's `note` is written in schema language ("a DataProvenance block",
  // "data_kind (live|cached|sample|synthetic)") — correct for /docs, wrong for a
  // page a fisher or an officer reads. The same promise is stated in plain
  // English below. The API field is unchanged; we just stop echoing it.

  const { data: probes = {} } = useQuery({
    queryKey: ['pillar-probes', pillars.map((p) => `${p.pillar_id}:${p.status}`).join('|')],
    queryFn: () => probeAll(pillars),
    enabled: !usingFixture && pillars.some((p) => p.status === 'live'),
  })

  const liveCount = pillars.filter((p) => p.status === 'live').length
  const reported = Object.keys(probes).length
  // Counted from real probes only, so the summary can never overstate how much
  // of the platform is running on live data.
  const kindCounts = Object.values(probes).reduce<Record<string, number>>((acc, probe) => {
    const k = probe.provenance.data_kind
    acc[k] = (acc[k] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="lk-scope pil-page">
      <header className="pil-head">
        <h1><Layers size={28} aria-hidden="true" /> {t('pillars.title')}</h1>
        <Badge tone="neutral">
          <span className="pil-data">{liveCount}</span>
          {' / '}<span className="pil-data">{pillars.length}</span> {t('pillars.liveCount')}
        </Badge>
      </header>

      <p className="pil-intro">{t('pillars.intro')}</p>

      {/* 5d: the at-a-glance data summary. */}
      {reported > 0 && (
        <div className="pil-kind-summary">
          <span className="pil-kind-summary__label">{t('pillars.dataSummary')}</span>
          {(['live', 'cached', 'sample', 'synthetic'] as DataKind[])
            .filter((k) => kindCounts[k])
            .map((k) => (
              <Badge key={k} tone={KIND_TONE[k]}>
                <span className="pil-data">{kindCounts[k]}</span> {t(`pillars.kind.${k}`)}
              </Badge>
            ))}
          {liveCount > reported && (
            <Badge tone="neutral" icon={<HelpCircle size={14} aria-hidden="true" />}>
              <span className="pil-data">{liveCount - reported}</span> {t('pillars.notReported')}
            </Badge>
          )}
        </div>
      )}

      {usingFixture && !isLoading && (
        <p className="pil-offline-note" role="status">{t('pillars.offlineNote')}</p>
      )}

      {isLoading ? (
        <Skeleton text count={4} />
      ) : (
        <div className="pil-grid">
          {pillars.map((p) => {
            const probe = probes[p.pillar_id]
            return (
              <Card
                key={p.pillar_id}
                title={p.pillar_name}
                action={<PillarStatusBadge pillar={p} />}
                raised={p.status === 'live'}
              >
                {/* data_kind first — it is what a viewer most needs to know. */}
                {probe ? (
                  <div className="pil-card__prov">
                    <ProvenanceBadge provenance={probe.provenance} compact />
                  </div>
                ) : p.status === 'live' ? (
                  <p className="pil-card__noprov">
                    <HelpCircle size={14} aria-hidden="true" /> {t('pillars.noProvenance')}
                  </p>
                ) : null}

                <p className="pil-card__desc">{p.description}</p>
                {/* The "Owner: Dhanesh (WS2)" row is gone — internal workstream
                    attribution, not information for anyone using the app. The
                    field still exists on the API for our own bookkeeping. */}
                <dl className="pil-card__facts">
                  <div>
                    <dt>{t('pillars.sources')}</dt>
                    <dd>
                      {p.sources.length === 0 ? '—' : p.sources.map((s) => (
                        <span key={s.name} className="pil-source">
                          {s.name}
                          <Badge tone={s.status === 'verified' ? 'success' : s.status === 'candidate' ? 'warning' : 'neutral'}>
                            {t(`pillars.source.${s.status}`)}
                          </Badge>
                        </span>
                      ))}
                    </dd>
                  </div>
                </dl>
                <Link to={`/pillars/${p.pillar_id}`} className="pil-card__link">
                  {t('pillars.viewDetail')} <ArrowRight size={16} aria-hidden="true" />
                </Link>
              </Card>
            )
          })}
        </div>
      )}

      <p className="pil-contract-note">{t('pillars.provenanceContract')}</p>

      {/* Badge reference, labelled as examples: no live pillar currently produces
          sample or synthetic output, and inventing one to complete the set is the
          exact dishonesty this component exists to prevent. */}
      <section className="pil-badge-ref">
        <h2>{t('pillars.badgeRefTitle')}</h2>
        <p className="pil-intro">{t('pillars.badgeRefBody')}</p>
        <div className="pil-badge-ref__list">
          {BADGE_EXAMPLES.map((prov) => (
            <ProvenanceBadge key={prov.data_kind} provenance={prov} />
          ))}
        </div>
      </section>
    </div>
  )
}
