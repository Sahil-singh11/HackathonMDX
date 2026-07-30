/* Marine Transport & Trade surface — /pillars/transport.
 *
 * LEADS WITH LIVE DATA. This surface previously showed a vessel arrivals table
 * built from SYNTHETIC AIS, because terrestrial AIS needs a receiver within
 * ~40 nm and Mauritius has none (satellite AIS covers it but is a paid
 * product). Generated vessels presented as content was the one genuinely
 * dishonest thing on the page, so the pillar now shows what was always real:
 * live Open-Meteo sea state at the Port Louis approach, turned into transit
 * windows by fixed thresholds in Python.
 *
 * The split of responsibility is the same as everywhere else in this app, and
 * it is stated on the page rather than only in this comment: every band and
 * figure is computed deterministically (transport/transit.py, unit-tested);
 * the narrative is model prose ABOUT those numbers, with `narrative_source`
 * deciding which of two visually distinct states renders. A fallback dressed
 * up as model output would be exactly the overclaim these rules exist to stop.
 */
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle, Bot, Calculator, CheckCircle2, HelpCircle, RefreshCw, Waves, XCircle,
} from 'lucide-react'
import { api } from '../../api/client'
import { Badge, Button, Card, Skeleton } from '../../components/ui'
import { useT } from '../../i18n'
import ProvenanceBadge from '../ProvenanceBadge'
import ApproachMap from './ApproachMap'
import type { Band, CraftWindow } from './types'
import './transport.css'

/** Colour is never the only signal: every band carries an icon and a word. */
const BAND_STYLE: Record<Band, { tone: 'success' | 'warning' | 'danger' | 'neutral'; icon: typeof CheckCircle2 }> = {
  good: { tone: 'success', icon: CheckCircle2 },
  moderate: { tone: 'warning', icon: AlertTriangle },
  poor: { tone: 'danger', icon: XCircle },
  unknown: { tone: 'neutral', icon: HelpCircle },
}

function Reading({ label, value, unit }: { label: string; value: number | null; unit: string }) {
  return (
    <div className="tpt-reading">
      <span className="tpt-reading__label">{label}</span>
      {/* An em-dash, never a 0: a missing reading is not a calm sea. */}
      <span className="tpt-reading__value pil-data">
        {value == null ? '—' : `${value} ${unit}`}
      </span>
    </div>
  )
}

function CraftCard({ craft }: { craft: CraftWindow }) {
  const t = useT()
  const style = BAND_STYLE[craft.overall] ?? BAND_STYLE.unknown
  const Icon = style.icon
  return (
    <div className={`tpt-craft tpt-craft--${craft.overall}`}>
      <div className="tpt-craft__head">
        <Badge tone={style.tone} icon={<Icon size={14} aria-hidden="true" />}>
          {t(`transport.band.${craft.overall}`)}
        </Badge>
        <strong>{craft.craft}</strong>
      </div>
      <p className="small tpt-craft__why">
        {t('transport.limitedBy')} <strong>{craft.limiting_factor}</strong>
      </p>
      {/* The actual numbers, printed so a reader can disagree with the bands
          rather than having to trust them. */}
      <p className="small tpt-note">{craft.thresholds_note}</p>
    </div>
  )
}

export default function TransportSurface() {
  const t = useT()
  const { data: brief, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['transportApproach'],
    queryFn: api.transportApproach,
    staleTime: 5 * 60_000,
    retry: false,           // a single attempt can legitimately take ~60 s
  })

  if (isLoading) {
    return (
      <Card title={t('transport.approachTitle')}>
        <Skeleton text count={4} />
        <p className="small tpt-patience">{t('transport.loadingNote')}</p>
      </Card>
    )
  }

  if (isError || !brief) {
    return (
      <Card title={t('transport.approachTitle')}>
        <p>{t('transport.errorBody')}</p>
        <p className="small pil-data">{error instanceof Error ? error.message : ''}</p>
        <Button variant="secondary" onClick={() => refetch()} loading={isFetching}
          icon={<RefreshCw size={16} aria-hidden="true" />}>
          {t('common.retry')}
        </Button>
      </Card>
    )
  }

  const modelWrote = brief.narrative_source === 'model'

  return (
    <div className="tpt">
      <ProvenanceBadge provenance={brief.provenance} />

      <Card
        title={`${t('transport.approachTitle')} — ${brief.port.name}`}
        action={
          <Button variant="ghost" onClick={() => refetch()} loading={isFetching}
            icon={<RefreshCw size={16} aria-hidden="true" />}>
            {t('common.retry')}
          </Button>
        }
      >
        <ApproachMap brief={brief} />
        {/* HTML, not canvas pixels: translatable, screen-readable, and it
            carries the one claim the map must not overstate. */}
        <p className="small tpt-legend">{t('transport.mapLegend')}</p>

        <h3 className="tpt-section">{t('transport.transitTitle')}</h3>
        <div className="tpt-crafts">
          {brief.crafts.map((c) => <CraftCard key={c.craft} craft={c} />)}
        </div>

        {brief.long_swell_flag && (
          <p className="banner warn tpt-swell">
            <Waves size={16} aria-hidden="true" /> {brief.long_swell_note}
          </p>
        )}
        {brief.incomplete && (
          <p className="small tpt-note">{t('transport.incompleteNote')}</p>
        )}
      </Card>

      <Card title={t('transport.readingsTitle')}>
        <div className="tpt-readings">
          <Reading label={t('marine.waveHeight')} value={brief.wave_height_m} unit="m" />
          <Reading label={t('marine.wavePeriod')} value={brief.wave_period_s} unit="s" />
          <Reading label={t('marine.swellHeight')} value={brief.swell_height_m} unit="m" />
          <Reading label={t('marine.swellPeriod')} value={brief.swell_period_s} unit="s" />
          <Reading label={t('transport.wind')} value={brief.wind_speed_kmh} unit="km/h" />
          <Reading label={t('transport.gusts')} value={brief.wind_gusts_kmh} unit="km/h" />
          <Reading label={t('marine.sst')} value={brief.sea_surface_temperature_c} unit="°C" />
        </div>
        {brief.observed_at && (
          <p className="small tpt-note">
            {t('marine.updated')} <span className="pil-data">{brief.observed_at}</span>
          </p>
        )}
      </Card>

      <Card title={t('transport.narrativeTitle')}>
        {/* The two sources are visually distinct ON PURPOSE — see file header. */}
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

        {/* scope_note verbatim, always. */}
        <p className="banner mockline tpt-scope">{brief.scope_note}</p>
      </Card>
    </div>
  )
}
