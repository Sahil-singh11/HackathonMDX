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
 */
import { useQuery } from '@tanstack/react-query'
import { Activity, Info, MapPin, ShieldAlert, Waves, Wind } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import { Badge, Card, Select, Skeleton } from '../../components/ui'
import { useT } from '../../i18n'
import { useOffline } from '../../lib/offline'
import ProvenanceBadge from '../ProvenanceBadge'
import type { DataProvenance } from '../types'
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

const ACTIVITIES = ['swimming', 'snorkelling', 'diving', 'windsurfing', 'kitesurfing'] as const

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
  const { online } = useOffline()
  const [activity, setActivity] = useState<string>('snorkelling')
  const [cached, setCached] = useState<{ payload: TourismBrief; storedAt: string } | null>(null)

  const key = useMemo(() => briefKey([], activity), [activity])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tourism-brief', activity],
    // The client types this loosely (Record<string, unknown>) so api/client.ts
    // does not have to mirror every pillar's schema; the narrowing happens here.
    queryFn: () => api.tourismBrief({ activity }).then((r) => r as unknown as TourismBrief),
    retry: 0,
    enabled: online,
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

  const brief = data ?? cached?.payload ?? null
  const servedFromCache = !data && !!cached

  // A stored brief is `cached` as of when it was stored — never re-presented
  // with its original data_kind.
  const provenance: DataProvenance | null = brief
    ? (servedFromCache
      ? { ...brief.provenance, data_kind: 'cached', retrieved_at: cached!.storedAt }
      : brief.provenance)
    : null

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

      {sitesInOrder.map((site, i) => {
        const forActivity = site.ratings.find((r) => r.activity === activity)
        return (
          <Card
            key={site.site_id}
            title={
              <span className="tou-site-title">
                {brief.ranking.length > 0 && <span className="tou-rank tou-data">#{i + 1}</span>}
                {site.name}
                <span className="tou-region"><MapPin size={14} aria-hidden="true" /> {site.region}</span>
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

            <h4 className="tou-section"><Waves size={16} aria-hidden="true" /> {t('tourism.measured')}</h4>
            <dl className="tou-figures">
              <Figure label={t('tourism.waveHeight')} value={site.measurements.wave_height_m} unit="m" />
              <Figure label={t('tourism.wavePeriod')} value={site.measurements.wave_period_s} unit="s" />
              <Figure label={t('tourism.swell')} value={site.measurements.swell_height_m} unit="m" />
              <Figure label={t('tourism.wind')} value={site.measurements.wind_speed_kmh} unit="km/h" />
              <Figure label={t('tourism.gusts')} value={site.measurements.wind_gusts_kmh} unit="km/h" />
              <Figure label={t('tourism.visibility')} value={site.measurements.visibility_m} unit="m" />
              <Figure label={t('tourism.seaTemp')} value={site.measurements.sea_surface_temperature_c} unit="°C" />
            </dl>

            <h4 className="tou-section"><Wind size={16} aria-hidden="true" /> {t('tourism.suitability')}</h4>
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

            {site.interpretation ? (
              <div className="tou-interpretation">
                <h4 className="tou-section">{t('tourism.interpretation')}</h4>
                <p>{site.interpretation}</p>
                <p className="tou-interpretation__note">{t('tourism.interpretationNote')}</p>
              </div>
            ) : (
              <p className="tou-no-interpretation">{t('tourism.noInterpretation')}</p>
            )}
          </Card>
        )
      })}
    </div>
  )
}
