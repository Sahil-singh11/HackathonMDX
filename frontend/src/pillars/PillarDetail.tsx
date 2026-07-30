/* /pillars/:id detail — the frame each pillar surface renders into.
 *
 * NOTHING DEVELOPER-FACING ON THIS PAGE. It previously showed an "Endpoints"
 * card listing /api/ routes, the literal 503 an unimplemented pillar would
 * answer with, an owner attribution, and source descriptions carrying file
 * paths and version strings. All of that was reference material for us, not
 * information for a user, and it is gone. The routes are still documented at
 * /docs; ownership still lives in the registry, just not on screen.
 *
 * To add a surface, register it in PILLAR_SURFACES below. Nothing else in this
 * folder should need editing.
 */
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Layers } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Badge, Card, EmptyState, Skeleton } from '../components/ui'
import FinancePanel from '../components/pillars/finance/FinancePanel'
import { useT } from '../i18n'
import EnergySurface from './energy/EnergySurface'
import { FIXTURE_PILLARS } from './fixture'
import { PillarStatusBadge } from './PillarsIndex'
import TourismSurface from './tourism/TourismSurface'
import TransportSurface from './transport/TransportSurface'
import './pillars.css'

/**
 * Extension point: map a pillar_id to its surface component.
 *
 * Adding an entry here is the whole integration step for a pillar owner; the
 * shell handles heading, provenance placement, enabled-state and not-found.
 *
 * A surface is only reached when the pillar is enabled — the not-enabled state
 * below wins otherwise, so a merged-but-disabled surface can never render
 * output the API would refuse to serve.
 */
export const PILLAR_SURFACES: Record<string, ReactNode> = {
  energy: <EnergySurface />,
  finance: <FinancePanel />,
  tourism: <TourismSurface />,
  transport: <TransportSurface />,
}

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

  // Gate on enabled, not merely on "a surface exists": a registered-but-disabled
  // pillar answers 503, so rendering its surface would show a panel whose data
  // the API refuses to serve. The not-enabled state below must win.
  const surface = pillar.status === 'live' ? PILLAR_SURFACES[pillar.pillar_id] : undefined

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

      {/* Real provenance, kept: name + verification badge + one short line.
          `s.description` is that line. It used to carry internal notes ("data/
          rules/species_rules.json (v1.1.0) — local, versioned", "Already
          integrated and cached by the app"); those were rewritten in the
          registry, so the render is unchanged and the content is now readable. */}
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
              {s.description && <p>{s.description}</p>}
            </li>
          ))}
        </ul>
      </Card>

      {/* The "Endpoints" card that listed /api/ routes is gone — it was
          developer reference material on a user-facing page. The routes are
          still documented at /docs. */}

      {surface ?? (
        pillar.status === 'live'
          ? (
            /* Fisheries: this pillar runs on the main app's own screens, so link
               straight to them instead of describing the architecture. */
            <Card title={t('pillars.liveElsewhereTitle')}>
              <p>{t('pillars.liveElsewhereBody')}</p>
              <ul className="pil-jump-list">
                <li><Link to="/record">{t('nav.catch')}</Link></li>
                <li><Link to="/log">{t('nav.history')}</Link></li>
                <li><Link to="/declaration">{t('nav.declaration')}</Link></li>
              </ul>
            </Card>
          )
          : (
            /* Not implemented in this build. One muted sentence — no barrier
               icon, no status code, no owner attribution. */
            <Card>
              <p className="pil-not-in-build">{t('pillars.notInBuild')}</p>
            </Card>
          )
      )}
    </div>
  )
}
