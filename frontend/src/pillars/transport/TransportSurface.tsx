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
import ProvenanceBadge, { providerLabel } from '../ProvenanceBadge'
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
  /* The STAND-IN vessel feed, fetched separately and on purpose.
   *
   * Its own provenance says data_kind='synthetic' — terrestrial AIS needs a
   * receiver within ~40 nm and none covers Mauritius, so this endpoint serves a
   * committed schema-accurate capture. It is here to show the arrivals surface
   * working, and it is rendered under a loud synthetic badge with the caveat in
   * HTML beside it. It is NEVER mixed into the live sea-state block above, and
   * the page still LEADS with the live data.
   *
   * A failure here must not take the live half of the page down, so this query is
   * independent and its error state is simply "no stand-in feed shown". */
  const { data: brief, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['transportApproach'],
    queryFn: api.transportApproach,
    staleTime: 5 * 60_000,
    retry: false,           // a single attempt can legitimately take ~60 s
  })

  /* GATED ON `brief`, and that gate is load-bearing.
   *
   * Both endpoints spend 30-100 s waiting on a model narrative, and the backend
   * serves them from a single worker, so firing them together made them queue —
   * the live sea state, which is the half that matters, ended up waiting behind a
   * demonstration feed. Measured: the page stopped rendering its transit windows
   * inside 200 s once this query ran in parallel.
   *
   * Ordering them puts the live data first and costs the demo feed nothing but
   * arriving second, which is exactly its priority. */
  const { data: arrivals } = useQuery({
    queryKey: ['transportArrivals'],
    queryFn: api.transportArrivals,
    staleTime: 5 * 60_000,
    retry: false,
    enabled: !!brief,
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
        {/* The raw `error.message` used to print here — "Request failed with
            status code 503" and friends. A status code is not an explanation for
            anyone reading this page, and errorBody already says what happened
            and what to do. The console still has the real message. */}
        <p>{t('transport.errorBody')}</p>
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
        <ApproachMap brief={brief} arrivals={arrivals} />
        {/* HTML, not canvas pixels: translatable, screen-readable, and it
            carries the one claim the map must not overstate. */}
        <p className="small tpt-legend">
          {arrivals ? t('transport.mapLegendStandIn') : t('transport.mapLegend')}
        </p>

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
              {providerLabel(brief.provenance.model_provider, t)}
            </p>
          </>
        ) : (
          <>
            <Badge tone="neutral" icon={<Calculator size={14} aria-hidden="true" />}>
              {t('transport.sourceMechanical')}
            </Badge>
            {/* `narrative_note` is no longer rendered. It carries the raw reason
                ("model call failed: The read operation timed out") — a Python
                exception string, which is for us, not for a reader. That the
                model was not involved IS user-facing, and the badge plus the
                sentence above already say it. The field stays on the API. */}
            <p className="small tpt-note tpt-source-why">{t('transport.narrativeFallback')}</p>
          </>
        )}

        <p className="tpt-narrative">{brief.narrative}</p>

        {/* scope_note verbatim, always. */}
        <p className="banner mockline tpt-scope">{brief.scope_note}</p>
      </Card>

      {/* STAND-IN DATA, LAST ON THE PAGE AND LOUDLY LABELLED.
          Below the live sea state, never above it, because the live half is what
          the pillar actually knows. ProvenanceBadge renders its `synthetic` state
          loud by design, and the coverage note and scope note ride verbatim. */}
      {arrivals && (
        <Card title={t('transport.arrivalsTitle')}>
          <ProvenanceBadge provenance={arrivals.provenance} />
          <p className="small tpt-note">{t('transport.bearingCaveat')}</p>

          <div className="tpt-congestion">
            {([
              ['transport.tracked', arrivals.congestion.vessels_tracked],
              ['transport.underWay', arrivals.congestion.under_way],
              ['transport.atAnchor', arrivals.congestion.at_anchor],
              ['transport.withinApproach', arrivals.congestion.within_approach_radius],
            ] as const).map(([key, value]) => (
              <div className="tpt-congestion__item" key={key}>
                <span className="tpt-congestion__label">{t(key)}</span>
                <span className="tpt-congestion__value pil-data">{value}</span>
              </div>
            ))}
          </div>
          {/* Verbatim: it says how the tally was made. */}
          <p className="small tpt-note">{arrivals.congestion.note}</p>

          <h3 className="tpt-section">{t('transport.expectedTitle')}</h3>
          <div className="tpt-arrivals">
            {[...arrivals.expected_arrivals]
              .sort((a, b) => a.distance_nm - b.distance_nm)
              .map((v) => (
                <div className="tpt-arrival" key={v.mmsi ?? v.vessel_name}>
                  <div className="tpt-arrival__head">
                    <strong>
                      {v.identity_known && v.vessel_name
                        ? v.vessel_name
                        : t('transport.vesselUnnamed')}
                    </strong>
                    <span className="tpt-arrival__range pil-data">
                      {v.distance_nm.toFixed(1)} nm
                    </span>
                  </div>
                  <p className="small tpt-arrival__meta">
                    {v.vessel_type} · {v.nav_status} ·{' '}
                    {/* An em-dash, never a 0 — a missing speed is not a stopped
                        vessel. The compiler caught this: speed_knots is nullable
                        because AIS position reports can omit it. */}
                    <span className="pil-data">
                      {v.speed_knots == null ? '—' : `${v.speed_knots.toFixed(1)} kn`}
                    </span>
                    {v.hours_to_reported_eta != null && (
                      <> · {t('transport.etaIn')}{' '}
                        <span className="pil-data">
                          {v.hours_to_reported_eta.toFixed(1)} h
                        </span>
                      </>
                    )}
                  </p>
                </div>
              ))}
          </div>

          {/* scope_note verbatim, always. */}
          <p className="banner mockline tpt-scope">{arrivals.scope_note}</p>
        </Card>
      )}
    </div>
  )
}
