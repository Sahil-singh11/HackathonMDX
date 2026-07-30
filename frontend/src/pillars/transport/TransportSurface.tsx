/* Marine Transport & Trade surface — /pillars/transport.
 *
 * Renders the Port Louis arrivals brief: the approach chart, the arrivals
 * table, congestion tally, sea state, and the narrative panel.
 *
 * The narrative panel is where Gemma faces the user, so it is also where the
 * split of responsibility must be visible: `narrative_source` says whether the
 * prose was written by the model or assembled deterministically, and the two
 * states are styled DIFFERENTLY on purpose — a fallback dressed up as model
 * output would be exactly the overclaim the honesty rules exist to prevent.
 *
 * Loading is patient by design: the narrative step waits on hosted Gemma and
 * can take up to 60 s before the backend falls back, so the skeleton says so
 * instead of looking hung. retry is off — one attempt is already a minute.
 */
import { useQuery } from '@tanstack/react-query'
import { Anchor, Bot, Calculator, RefreshCw, Ship } from 'lucide-react'
import { api } from '../../api/client'
import { Badge, Button, Card, Skeleton, Table, type Column } from '../../components/ui'
import { useT } from '../../i18n'
import ProvenanceBadge from '../ProvenanceBadge'
import ApproachMap from './ApproachMap'
import type { ArrivalEntry } from './types'
import './transport.css'

/** "14:30" in the viewer's own timezone; the ISO string stays in the title
 *  attribute so the exact reported value is one hover away. */
function localTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export default function TransportSurface() {
  const t = useT()
  const { data: brief, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['transportArrivals'],
    queryFn: api.transportArrivals,
    staleTime: 5 * 60_000,
    retry: false,           // a single attempt can legitimately take ~60 s
  })

  if (isLoading) {
    return (
      <Card title={t('transport.arrivalsTitle')}>
        <Skeleton text count={4} />
        <p className="small tpt-patience">{t('transport.loadingNote')}</p>
      </Card>
    )
  }

  if (isError || !brief) {
    return (
      <Card title={t('transport.arrivalsTitle')}>
        <p>{t('transport.errorBody')}</p>
        <p className="small pil-data">{error instanceof Error ? error.message : ''}</p>
        <Button variant="secondary" onClick={() => refetch()} loading={isFetching}
          icon={<RefreshCw size={16} aria-hidden="true" />}>
          {t('common.retry')}
        </Button>
      </Card>
    )
  }

  const c = brief.congestion
  const modelWrote = brief.narrative_source === 'model'

  // `data: true` puts the cell in the frozen Table's own mono role, which is
  // what CLAUDE.md wants for anything an officer would read aloud (ranges,
  // ETAs, MMSI) — no need to hand-roll a mono span per cell.
  const columns: Column<ArrivalEntry>[] = [
    {
      key: 'vessel', header: t('transport.vessel'), sortable: true,
      sortValue: (row) => row.vessel_name ?? String(row.mmsi),
      render: (row) => row.identity_known && row.vessel_name
        ? <strong>{row.vessel_name}</strong>
        : <span className="tpt-unknown">{t('transport.identityUnknown')} · <span className="pil-data">MMSI {row.mmsi}</span></span>,
    },
    { key: 'vessel_type', header: t('transport.type'), sortable: true },
    {
      key: 'reported_eta_utc', header: t('transport.eta'), sortable: true, data: true,
      sortValue: (row) => row.hours_to_reported_eta,
      render: (row) => (
        <span title={row.reported_eta_utc}>
          {localTime(row.reported_eta_utc)} · {row.hours_to_reported_eta.toFixed(1)} h
        </span>
      ),
    },
    {
      key: 'distance_nm', header: t('transport.range'), sortable: true, align: 'right', data: true,
      render: (row) => `${row.distance_nm.toFixed(1)} nm`,
    },
    {
      key: 'speed_knots', header: t('transport.speed'), align: 'right', data: true,
      render: (row) => (row.speed_knots != null ? `${row.speed_knots.toFixed(1)} kn` : '—'),
    },
  ]

  return (
    <div className="tpt">
      <ProvenanceBadge provenance={brief.provenance} />

      <Card
        title={`${t('transport.arrivalsTitle')} — ${brief.port.name}`}
        action={
          <Button variant="ghost" onClick={() => refetch()} loading={isFetching}
            icon={<RefreshCw size={16} aria-hidden="true" />}>
            {t('common.retry')}
          </Button>
        }
      >
        <p className="small">
          {brief.expected_arrivals_count} {t('transport.expectedIn')}{' '}
          <span className="pil-data">{brief.window_hours} h</span>
        </p>

        <ApproachMap brief={brief} />
        {/* The legend is HTML, not canvas pixels: translatable, findable by a
            screen reader, and impossible to miss — it carries the one claim
            the chart must not overstate. */}
        <p className="small tpt-legend">{t('transport.chartLegend')}</p>

        <Table<ArrivalEntry>
          columns={columns}
          rows={brief.expected_arrivals}
          rowKey={(row) => String(row.mmsi)}
          caption={t('transport.arrivalsTitle')}
          empty={t('transport.noArrivals')}
        />
      </Card>

      <Card title={t('transport.congestionTitle')}>
        <div className="tpt-tally" role="group" aria-label={t('transport.congestionTitle')}>
          <Badge tone="neutral" icon={<Ship size={14} aria-hidden="true" />}>
            {c.vessels_tracked} {t('transport.tracked')}
          </Badge>
          <Badge tone="accent">{c.under_way} {t('transport.underWay')}</Badge>
          <Badge tone="neutral" icon={<Anchor size={14} aria-hidden="true" />}>
            {c.at_anchor} {t('transport.atAnchor')}
          </Badge>
          <Badge tone="neutral">{c.moored} {t('transport.moored')}</Badge>
          <Badge tone="warning">{c.identity_unknown} {t('transport.identityUnknownCount')}</Badge>
        </div>
        <p className="small">
          {c.within_approach_radius} {t('transport.withinApproach')}{' '}
          <span className="pil-data">{c.approach_radius_nm} nm</span>
        </p>
        {/* Backend's own tally-honesty note, verbatim. */}
        <p className="small tpt-note">{c.note}</p>
      </Card>

      <Card title={t('transport.conditionsTitle')}>
        <div className="tpt-conditions">
          <div><span className="tpt-cond-label">{t('marine.waveHeight')}</span>
            <span className="pil-data">{brief.conditions.wave_height_m ?? '—'} m</span></div>
          <div><span className="tpt-cond-label">{t('marine.swellHeight')}</span>
            <span className="pil-data">{brief.conditions.swell_height_m ?? '—'} m</span></div>
          <div><span className="tpt-cond-label">{t('marine.swellPeriod')}</span>
            <span className="pil-data">{brief.conditions.swell_period_s ?? '—'} s</span></div>
          <div><span className="tpt-cond-label">{t('marine.sst')}</span>
            <span className="pil-data">{brief.conditions.sea_surface_temperature_c ?? '—'} °C</span></div>
        </div>
        <p className="small tpt-note">
          {t('marine.source')}: <span className="pil-data">{brief.conditions.source}</span>
        </p>
      </Card>

      <Card title={t('transport.narrativeTitle')}>
        {/* The two sources are visually distinct ON PURPOSE — see file header. */}
        {/* Badge carries a SHORT label only; the full explanation is a
            paragraph beneath it. A sentence inside a Badge does not wrap and
            measured 458px wide, overflowing a 390px phone. */}
        {modelWrote ? (
          <>
            <Badge tone="accent" icon={<Bot size={14} aria-hidden="true" />}>
              {t('transport.sourceModel')}
            </Badge>
            <p className="small tpt-note tpt-source-why">
              {t('transport.narrativeByModel')}{' '}
              <span className="pil-data">{brief.provenance.model_provider}</span>
            </p>
          </>
        ) : (
          <>
            <Badge tone="neutral" icon={<Calculator size={14} aria-hidden="true" />}>
              {t('transport.sourceMechanical')}
            </Badge>
            <p className="small tpt-note tpt-source-why">{t('transport.narrativeFallback')}</p>
            {brief.narrative_note && (
              <p className="small tpt-note tpt-fallback-why">
                {t('transport.fallbackWhy')} <span className="pil-data">{brief.narrative_note}</span>
              </p>
            )}
          </>
        )}

        <p className="tpt-narrative">{brief.narrative}</p>

        {modelWrote && (
          <>
            <h3 className="tpt-risk-head">{t('transport.riskTitle')}</h3>
            <p className="tpt-narrative">{brief.risk_reasoning}</p>
          </>
        )}

        {/* scope_note verbatim, always, styled like the app's other permanent
            disclaimers — this is the "advisory only" line. */}
        <p className="banner mockline tpt-scope">{brief.scope_note}</p>
      </Card>
    </div>
  )
}
