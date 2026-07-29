/* Workstream 2 — /pillars index.
 *
 * Lists all six national pillars with their real registry state. Reads
 * /api/pillars when reachable and falls back to the committed fixture when it
 * is not, so the page works with the backend down — and says which of the two
 * it used rather than letting a stale list pass as current.
 *
 * Live/registered comes from the backend's own derived state (implemented AND
 * opted in via PILLARS_ENABLED). We never infer or assume it: a pillar that has
 * merged but is not enabled must read as "registered", because that is what a
 * caller would actually get (503).
 */
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, CircleDot, Layers } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { Badge, Card, Skeleton } from '../components/ui'
import { useT } from '../i18n'
import ProvenanceBadge from './ProvenanceBadge'
import { BADGE_EXAMPLES, FIXTURE_NOTE, FIXTURE_PILLARS } from './fixture'
import './pillars.css'
import type { PillarDescriptor } from './types'

export function PillarStatusBadge({ pillar }: { pillar: PillarDescriptor }) {
  const t = useT()
  return pillar.status === 'live'
    ? <Badge tone="success" icon={<CircleDot size={14} aria-hidden="true" />}>{t('pillars.status.live')}</Badge>
    : <Badge tone="neutral">{t('pillars.status.registered')}</Badge>
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
  const note = data?.note ?? FIXTURE_NOTE

  return (
    <div className="lk-scope pil-page">
      <header className="pil-head">
        <h1><Layers size={28} aria-hidden="true" /> {t('pillars.title')}</h1>
        <Badge tone="neutral">
          <span className="pil-data">{pillars.filter((p) => p.status === 'live').length}</span>
          {' / '}<span className="pil-data">{pillars.length}</span> {t('pillars.liveCount')}
        </Badge>
      </header>

      <p className="pil-intro">{t('pillars.intro')}</p>

      {usingFixture && !isLoading && (
        <p className="pil-offline-note" role="status">{t('pillars.offlineNote')}</p>
      )}

      {isLoading ? (
        <Skeleton text count={4} />
      ) : (
        <div className="pil-grid">
          {pillars.map((p) => (
            <Card
              key={p.pillar_id}
              title={p.pillar_name}
              action={<PillarStatusBadge pillar={p} />}
              raised={p.status === 'live'}
            >
              <p className="pil-card__desc">{p.description}</p>
              <dl className="pil-card__facts">
                <div><dt>{t('pillars.owner')}</dt><dd>{p.owner || '—'}</dd></div>
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
          ))}
        </div>
      )}

      <p className="pil-contract-note">{note}</p>

      {/* Badge reference. Explicitly labelled as examples — only `fisheries` is
          implemented today, so no live pillar can yet produce sample/synthetic
          output, and inventing one to fill the demo would be the exact
          dishonesty this component exists to prevent. */}
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
