/* Workstream 2 — /pillars/:id detail.
 *
 * The frame the other two workstreams render into. A pillar that is registered
 * but not enabled shows exactly that, including the 503 a caller would get —
 * it never shows an empty panel that could be mistaken for "no results".
 *
 * Yadhav / Shirish: to add your surface, render it in the `children` slot via
 * PILLAR_SURFACES below (or pass it from your own route). You should not need
 * to edit anything else in this folder.
 */
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Construction, Layers } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Badge, Card, EmptyState, Skeleton } from '../components/ui'
import { useT } from '../i18n'
import { PillarStatusBadge } from './PillarsIndex'
import { FIXTURE_PILLARS } from './fixture'
import './pillars.css'

/**
 * Extension point: map a pillar_id to its surface component.
 *
 * Empty by design at 5a — the shell lands before the content. Adding an entry
 * here is the whole integration step for a pillar owner; the shell handles
 * heading, provenance placement, enabled-state and not-found for you.
 */
export const PILLAR_SURFACES: Record<string, ReactNode> = {}

export default function PillarDetail() {
  const t = useT()
  const { id = '' } = useParams<{ id: string }>()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['pillars'],
    queryFn: api.pillars,
    retry: 1,
  })

  const pillars = (isError || !data) ? FIXTURE_PILLARS : data.pillars
  const pillar = pillars.find((p) => p.pillar_id === id)

  if (isLoading) {
    return <div className="lk-scope pil-page"><Skeleton text count={3} /></div>
  }

  if (!pillar) {
    return (
      <div className="lk-scope pil-page">
        <Card>
          <EmptyState
            icon={<Layers size={48} aria-hidden="true" />}
            title={t('pillars.notFoundTitle')}
            body={<>{t('pillars.notFoundBody')} <span className="pil-data">{id || '—'}</span></>}
            action={<Link to="/pillars" className="pil-card__link">{t('pillars.backToIndex')}</Link>}
          />
        </Card>
      </div>
    )
  }

  const surface = PILLAR_SURFACES[pillar.pillar_id]

  return (
    <div className="lk-scope pil-page">
      <Link to="/pillars" className="pil-back">
        <ArrowLeft size={16} aria-hidden="true" /> {t('pillars.backToIndex')}
      </Link>

      <header className="pil-head">
        <h1>{pillar.pillar_name}</h1>
        <PillarStatusBadge pillar={pillar} />
      </header>

      <p className="pil-intro">{pillar.description}</p>

      <Card title={t('pillars.declaredSources')}>
        <ul className="pil-source-list">
          {pillar.sources.length === 0 && <li>{t('pillars.noSources')}</li>}
          {pillar.sources.map((s) => (
            <li key={s.name}>
              <div className="pil-source-list__head">
                <strong>
                  {s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.name}</a> : s.name}
                </strong>
                <Badge tone={s.status === 'verified' ? 'success' : s.status === 'candidate' ? 'warning' : 'neutral'}>
                  {t(`pillars.source.${s.status}`)}
                </Badge>
              </div>
              <p>{s.description}</p>
            </li>
          ))}
        </ul>
      </Card>

      {pillar.endpoints.length > 0 && (
        <Card title={t('pillars.endpoints')}>
          <ul className="pil-endpoints pil-data">
            {pillar.endpoints.map((e) => <li key={e}>{e}</li>)}
          </ul>
        </Card>
      )}

      {surface ?? (
        <Card>
          <EmptyState
            icon={<Construction size={48} aria-hidden="true" />}
            title={t(pillar.status === 'live' ? 'pillars.liveElsewhereTitle' : 'pillars.notEnabledTitle')}
            body={
              pillar.status === 'live'
                ? <>{t('pillars.liveElsewhereBody')}</>
                : <>
                  {t('pillars.notEnabledBody')}
                  <br /><br />
                  <span className="pil-data">
                    GET /api/pillars/{pillar.pillar_id}/… → 503
                  </span>
                  <br /><br />
                  <strong>{t('pillars.owner')}:</strong> {pillar.owner || '—'}
                </>
            }
          />
        </Card>
      )}
    </div>
  )
}
