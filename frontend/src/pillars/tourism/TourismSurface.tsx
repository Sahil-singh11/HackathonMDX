/* Workstream 2 — Sustainable Ocean Tourism surface.
 *
 * Renders deterministic figures and model prose as visibly different things:
 * measurements and ratings are mono-formatted data with their thresholds cited,
 * the interpretation sits in a labelled block that says a model wrote it.
 *
 * The ranking carries its "conditions, not crowding" caveat ON THE SURFACE, not
 * only in coverage_note, because that is the claim a reader is most likely to
 * over-interpret — "best site today" reads as "quietest site today" unless you
 * say otherwise in the same eyeline.
 *
 * THE CHART (SiteChart.tsx) is an index, not a replacement. It plots each site
 * at its published coordinate and shows how today's conditions rate there; the
 * full brief for every site still renders below, in ranking order, exactly as
 * before. Selecting on the chart or in the button list moves you to a card —
 * it never hides one. Nothing on this page is reachable only by pointer.
 */
import { useQuery } from '@tanstack/react-query'
import { Activity, Compass, Info, MapPin, ShieldAlert, Waves, Wind } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../../api/client'
import { Badge, Card, Select, Skeleton } from '../../components/ui'
import { useT } from '../../i18n'
import { useAnnounce } from '../../lib/announce'
import { useOffline } from '../../lib/offline'
import { useTheme } from '../../theme'
import ProvenanceBadge from '../ProvenanceBadge'
import type { DataProvenance } from '../types'
import BandGlyph, { ProtectedGlyph } from './BandGlyph'
import TourismMap, { type ChartSite } from './TourismMap'
import { bandOf, type Band } from './chartGeometry'
import { briefKey, getBrief, putBrief } from './briefCache'
import './tourism.css'

interface Measurements {
  wave_height_m: number | null
  wave_period_s: number | null
  swell_height_m: number | null
  wind_speed_kmh: number | null
  wind_gusts_kmh: number | null
  visibility_m: number | null
  sea_surface_temperature_c: number | null
  observed_at: string | null
}
interface Rating { activity: string; rating: string; score: number; reasons: string[] }
interface SiteBrief {
  site_id: string; name: string; region: string; character: string
  protected_area: boolean; protected_area_note: string
  measurements: Measurements; ratings: Rating[]; interpretation: string
}
interface TourismBrief {
  provenance: DataProvenance
  sites: SiteBrief[]
  ranked_for_activity: string | null
  ranking: Array<{ site_id: string; rating: string; score: number; reasons: string[] }>
  ranking_basis: string
}

/** GET /api/pillars/tourism/sites — the versioned catalogue on disk. */
interface CatalogueSite {
  site_id: string; name: string; region: string
  latitude: number; longitude: number
  character: string; typical_activities: string[]
  protected_area: boolean; protected_area_note: string
}
interface SiteCatalogue {
  sites_version: string
  generated: string
  /** Verbatim. Says these coordinates are area centres, not survey positions. */
  disclaimer: string
  coverage_note: string
  activities: string[]
  sites: CatalogueSite[]
}

/** What the chart and the button list both need for one site. */
interface SiteRow extends ChartSite { region: string }

const ACTIVITIES = ['swimming', 'snorkelling', 'diving', 'windsurfing', 'kitesurfing'] as const
const BANDS: Band[] = ['good', 'fair', 'poor', 'unknown']

/* The catalogue rides in the same IndexedDB store as the briefs, under a key
 * that cannot collide with briefKey()'s `ids::activity` shape. Coordinates are
 * static versioned data, so a stored copy stays correct offline — but it is
 * still labelled as a stored copy, never presented as a fresh read. */
const SITES_CACHE_KEY = 'catalogue::sites'

/**
 * Is this interpretation actually prose, or a raw model envelope?
 *
 * A LIVE BUG this guards against: /api/pillars/tourism/brief currently returns
 * the router's chat-intent envelope in `interpretation` for some sites —
 * ```json {"intent":"other","reply":"I am the Lamer Konekte assistant..."}```
 * — measured on 2 of 8 sites (Trou aux Biches, Belle Mare). Rendered as-is that
 * puts a chatbot refusal on screen labelled as a tourism interpretation, which
 * is both an honesty failure and the most visible thing on the page in a demo.
 *
 * This does NOT hide the backend bug — the real fix belongs in
 * backend/app/pillars/tourism/module.py (Lane B) and is reported there. What it
 * does is route a malformed payload into the "no interpretation" state the
 * surface ALREADY has and which 6 of 8 sites legitimately use today. The
 * backend's own docstring says a missing sentence is honest and a fabricated
 * one is not; a chat refusal presented as analysis is the fabricated case.
 *
 * Deliberately narrow: it only rejects text that opens a fenced/JSON block or
 * carries the router's own keys. Ordinary prose mentioning a brace is fine.
 */
function isProse(text: string | null | undefined): boolean {
  if (!text) return false
  const t = text.trim()
  if (!t) return false
  if (t.startsWith('```') || t.startsWith('{') || t.startsWith('json')) return false
  return !/"(intent|reply|tool|needs_more_information)"\s*:/.test(t)
}

function ratingTone(rating: string): 'success' | 'warning' | 'danger' | 'neutral' {
  return rating === 'good' ? 'success' : rating === 'fair' ? 'warning'
    : rating === 'poor' ? 'danger' : 'neutral'
}

function Figure({ label, value, unit }: { label: string; value: number | null; unit: string }) {
  const t = useT()
  return (
    <div className="tou-figure">
      <dt>{label}</dt>
      <dd className="tou-data">
        {value == null ? <span className="tou-unavailable">{t('tourism.unavailable')}</span>
          : <>{value}<span className="tou-unit"> {unit}</span></>}
      </dd>
    </div>
  )
}

export default function TourismSurface() {
  const t = useT()
  const announce = useAnnounce()
  // ChartMap owns the Sunlight case now, so this surface no longer needs `theme`.
  const { reduceMotion } = useTheme()
  const { online } = useOffline()
  const [activity, setActivity] = useState<string>('snorkelling')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [cached, setCached] = useState<{ payload: TourismBrief; storedAt: string } | null>(null)
  const [cachedSites, setCachedSites] = useState<{ payload: SiteCatalogue; storedAt: string } | null>(null)
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({})

  const key = useMemo(() => briefKey([], activity), [activity])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tourism-brief', activity],
    // The client types this loosely (Record<string, unknown>) so api/client.ts
    // does not have to mirror every pillar's schema; the narrowing happens here.
    queryFn: () => api.tourismBrief({ activity }).then((r) => r as unknown as TourismBrief),
    retry: 0,
    enabled: online,
  })

  // The catalogue is static versioned JSON, so it is fetched once and never
  // refetched for an activity change — only the brief depends on activity.
  const { data: catalogueData, isLoading: sitesLoading } = useQuery({
    queryKey: ['tourism-sites'],
    queryFn: () => api.tourismSites().then((r) => r as unknown as SiteCatalogue),
    retry: 0,
    enabled: online,
    staleTime: Infinity,
  })

  // Persist every successful brief, and read the stored copy back when the
  // network call cannot run or fails.
  useEffect(() => { if (data) void putBrief(key, data) }, [data, key])
  useEffect(() => {
    if (data) return
    void getBrief<TourismBrief>(key).then((hit) => {
      if (hit) setCached({ payload: hit.payload, storedAt: hit.storedAt })
    })
  }, [data, key])

  useEffect(() => { if (catalogueData) void putBrief(SITES_CACHE_KEY, catalogueData) }, [catalogueData])
  useEffect(() => {
    if (catalogueData) return
    void getBrief<SiteCatalogue>(SITES_CACHE_KEY).then((hit) => {
      if (hit) setCachedSites({ payload: hit.payload, storedAt: hit.storedAt })
    })
  }, [catalogueData])

  const brief = data ?? cached?.payload ?? null
  const servedFromCache = !data && !!cached
  const catalogue = catalogueData ?? cachedSites?.payload ?? null
  const catalogueFromCache = !catalogueData && !!cachedSites

  // A stored brief is `cached` as of when it was stored — never re-presented
  // with its original data_kind.
  const provenance: DataProvenance | null = brief
    ? (servedFromCache
      ? { ...brief.provenance, data_kind: 'cached', retrieved_at: cached!.storedAt }
      : brief.provenance)
    : null

  /* One row per site the brief actually returned, in ranking order. A site in
   * the catalogue but missing from the brief is dropped rather than plotted
   * with an invented rating. */
  const rows: SiteRow[] = useMemo(() => {
    if (!catalogue || !brief) return []
    const rankOf = new Map(brief.ranking.map((r, i) => [r.site_id, i + 1]))
    const briefOf = new Map(brief.sites.map((s) => [s.site_id, s]))
    return catalogue.sites
      .filter((s) => briefOf.has(s.site_id))
      .map((s) => ({
        site_id: s.site_id,
        name: s.name,
        region: s.region,
        latitude: s.latitude,
        longitude: s.longitude,
        protected_area: s.protected_area,
        band: bandOf(briefOf.get(s.site_id)!.ratings.find((r) => r.activity === activity)?.rating),
        rank: rankOf.get(s.site_id) ?? null,
      }))
      .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99))
  }, [catalogue, brief, activity])

  const select = useCallback((siteId: string) => {
    setSelectedId(siteId)
    const row = rows.find((r) => r.site_id === siteId)
    if (row) announce(`${row.name} — ${t(`tourism.rating.${row.band}`)}`)
    const el = cardRefs.current[siteId]
    if (el) {
      // Focus first without scrolling, then scroll deliberately, so the two do
      // not fight over the final position.
      el.focus({ preventScroll: true })
      el.scrollIntoView({ block: 'start', behavior: reduceMotion ? 'auto' : 'smooth' })
    }
  }, [rows, announce, t, reduceMotion])

  if (isLoading && !brief) return <Card><Skeleton text count={3} /></Card>

  if (!brief) {
    return (
      <Card title={t('tourism.title')}>
        <p>{t(isError || !online ? 'tourism.noCache' : 'tourism.loading')}</p>
      </Card>
    )
  }

  const rankedById = new Map(brief.ranking.map((r) => [r.site_id, r]))
  const sitesInOrder = brief.ranking.length > 0
    ? [...brief.sites].sort((a, b) =>
      (rankedById.get(b.site_id)?.score ?? 0) - (rankedById.get(a.site_id)?.score ?? 0))
    : brief.sites

  return (
    <div className="tou-surface">
      <Card title={t('tourism.title')}>
        <p className="tou-intro">{t('tourism.intro')}</p>

        <label className="tou-activity">
          <span>{t('tourism.activityLabel')}</span>
          <Select value={activity} onChange={(e) => setActivity(e.target.value)}>
            {ACTIVITIES.map((a) => <option key={a} value={a}>{t(`tourism.activity.${a}`)}</option>)}
          </Select>
        </label>

        {/* The caveat lives here, next to the ranking it qualifies. */}
        <p className="tou-ranking-basis" role="note">
          <Info size={16} aria-hidden="true" /> {brief.ranking_basis}
        </p>

        {provenance && <ProvenanceBadge provenance={provenance} />}
      </Card>

      <Card
        title={
          <span className="tou-site-title">
            <Compass size={20} aria-hidden="true" /> {t('tourism.chartTitle')}
          </span>
        }
      >
        {rows.length === 0 ? (
          // Never a spinner that never resolves: either the catalogue request is
          // still in flight, or it is genuinely not on this device and we say so.
          sitesLoading
            ? <Skeleton text count={2} />
            : <p className="tou-chart-off">{t('tourism.chartNoPositions')}</p>
        ) : (
          <>
            <p className="tou-intro">{t('tourism.chartIntro')}</p>

            <div className="tou-chart-layout">
              <div>
                <TourismMap sites={rows} selectedId={selectedId} onSelect={select} />

                <h3 className="tou-section">{t('tourism.markerKey')}</h3>
                <ul className="tou-legend">
                  {BANDS.map((b) => (
                    <li key={b}>
                      <BandGlyph band={b} /> {t(`tourism.rating.${b}`)}
                    </li>
                  ))}
                  <li><ProtectedGlyph /> {t('tourism.protectedMarker')}</li>
                </ul>
              </div>

              <div>
                <h3 className="tou-section">{t('tourism.chooseSite')}</h3>
                <p className="tou-computed-note">{t('tourism.chooseSiteHint')}</p>
                <ul className="tou-sitelist">
                  {rows.map((row) => {
                    const on = row.site_id === selectedId
                    return (
                      <li key={row.site_id}>
                        <button
                          type="button"
                          className={`tou-sitebtn${on ? ' tou-sitebtn--on' : ''}`}
                          aria-current={on ? 'true' : undefined}
                          onClick={() => select(row.site_id)}
                        >
                          <BandGlyph band={row.band} />
                          <span className="tou-sitebtn__body">
                            <span className="tou-sitebtn__name">
                              <span className="tou-data">
                                {row.rank ? `${row.rank}.` : '—'}
                              </span>{' '}
                              {row.name}
                            </span>
                            <span className="tou-sitebtn__meta">
                              {row.region} · {t(`tourism.rating.${row.band}`)}
                              {row.rank ? '' : ` · ${t('tourism.noRanking')}`}
                              {row.protected_area ? ` · ${t('tourism.protectedMarker')}` : ''}
                            </span>
                          </span>
                          {on && <span className="tou-sitebtn__on">{t('tourism.selectedSite')}</span>}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </div>
            </div>

            {/* Both notes are the API's own words. Do not paraphrase or trim
                either: the disclaimer is what stops this chart being read as a
                navigation aid, and it is the chart that makes it necessary. */}
            {catalogue && (
              <div className="tou-positions">
                <p><strong>{t('tourism.positionsNote')}</strong> {catalogue.disclaimer}</p>
                <p><strong>{t('pillars.coverage')}</strong> {catalogue.coverage_note}</p>
                <p className="tou-catalogue-meta">
                  {t('tourism.catalogueVersion')}{' '}
                  <span className="tou-data">{catalogue.sites_version}</span>
                  {' · '}
                  <span className="tou-data">{catalogue.generated}</span>
                  {catalogueFromCache ? ` · ${t('tourism.chartPositionsCached')}` : ''}
                </p>
              </div>
            )}
          </>
        )}
      </Card>

      {sitesInOrder.map((site, i) => {
        const forActivity = site.ratings.find((r) => r.activity === activity)
        const on = site.site_id === selectedId
        return (
          <div
            key={site.site_id}
            /* tabIndex -1 so selecting from the chart can move focus here
               without adding a stop to the normal tab order. */
            tabIndex={-1}
            ref={(el) => { cardRefs.current[site.site_id] = el }}
            className={`tou-site-anchor${on ? ' tou-site-anchor--on' : ''}`}
          >
            <Card
              title={
                <span className="tou-site-title">
                  {brief.ranking.length > 0 && <span className="tou-rank tou-data">#{i + 1}</span>}
                  {site.name}
                  <span className="tou-region"><MapPin size={14} aria-hidden="true" /> {site.region}</span>
                  {on && <Badge tone="accent">{t('tourism.selectedSite')}</Badge>}
                </span>
              }
              action={forActivity && (
                <Badge tone={ratingTone(forActivity.rating)} icon={<Activity size={14} aria-hidden="true" />}>
                  {t(`tourism.rating.${forActivity.rating}`)}
                </Badge>
              )}
            >
              <p className="tou-character">{site.character}</p>

              {site.protected_area && (
                <p className="tou-protected" role="note">
                  <ShieldAlert size={16} aria-hidden="true" /> {site.protected_area_note}
                </p>
              )}

              <h3 className="tou-section"><Waves size={16} aria-hidden="true" /> {t('tourism.measured')}</h3>
              <dl className="tou-figures">
                <Figure label={t('tourism.waveHeight')} value={site.measurements.wave_height_m} unit="m" />
                <Figure label={t('tourism.wavePeriod')} value={site.measurements.wave_period_s} unit="s" />
                <Figure label={t('tourism.swell')} value={site.measurements.swell_height_m} unit="m" />
                <Figure label={t('tourism.wind')} value={site.measurements.wind_speed_kmh} unit="km/h" />
                <Figure label={t('tourism.gusts')} value={site.measurements.wind_gusts_kmh} unit="km/h" />
                <Figure label={t('tourism.visibility')} value={site.measurements.visibility_m} unit="m" />
                <Figure label={t('tourism.seaTemp')} value={site.measurements.sea_surface_temperature_c} unit="°C" />
              </dl>

              <h3 className="tou-section"><Wind size={16} aria-hidden="true" /> {t('tourism.suitability')}</h3>
              <p className="tou-computed-note">{t('tourism.computedNote')}</p>
              <ul className="tou-ratings">
                {site.ratings.map((r) => (
                  <li key={r.activity}>
                    <Badge tone={ratingTone(r.rating)}>{t(`tourism.rating.${r.rating}`)}</Badge>
                    <strong>{t(`tourism.activity.${r.activity}`)}</strong>
                    <span className="tou-reasons tou-data">{r.reasons.join(' · ')}</span>
                  </li>
                ))}
              </ul>

              {isProse(site.interpretation) ? (
                <div className="tou-interpretation">
                  <h3 className="tou-section">{t('tourism.interpretation')}</h3>
                  <p>{site.interpretation}</p>
                  <p className="tou-interpretation__note">{t('tourism.interpretationNote')}</p>
                </div>
              ) : (
                /* Two DIFFERENT failures, stated differently. The existing
                   "could not be reached" copy is about an absent response; for a
                   malformed one the model did answer, so claiming it was
                   unreachable would be a false statement about what happened —
                   exactly the kind of small inaccuracy this project treats as a
                   real defect. */
                <p className="tou-no-interpretation">
                  {site.interpretation
                    ? t('tourism.interpretationUnusable')
                    : t('tourism.noInterpretation')}
                </p>
              )}
            </Card>
          </div>
        )
      })}
    </div>
  )
}
