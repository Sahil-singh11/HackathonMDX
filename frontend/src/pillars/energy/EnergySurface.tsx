/**
 * Ocean-Based Renewable Energy — converted to the shared pillar framework.
 *
 * PRESENTATION ONLY. The query, the endpoint and every number are unchanged:
 * wave and wind power density are still computed in Python
 * (backend/app/pillars/energy/resource.py) and this file still cannot produce or
 * alter a figure. What changed is the order a reader meets them in.
 *
 *   Answer   the best candidate site and its wave power density, one sentence,
 *            with that same figure as the hero number — read from the data, not
 *            recomputed here
 *   Figures  wave power, wind power, distance from shore, swell period
 *   Visual   ranked bar comparison across candidate sites
 *   Detail   per-site breakdown, each formula shown with its inputs substituted
 *   Method   the three formulas verbatim — folded because it is a strength that
 *            should be findable, not a wall that greets you
 *   Limits   nearshore overstatement, energy-period caveat, 10 m wind height
 *
 * WHAT MOVED AND WHY. The old layout put the "not a yield assessment, not a
 * survey" basis ABOVE the numbers, which was correct when the numbers were the
 * first thing on the page. Now the answer is first, so that text moves into
 * Limits — rendered verbatim and one click away, never paraphrased — and the
 * answer sentence itself stays modest by saying "indication" rather than
 * implying a yield figure.
 */
import { useQuery } from '@tanstack/react-query'
import { Waves, Wind } from 'lucide-react'
import { api } from '../../api/client'
import {
  Answer, BarComparison, FigureRow, Foldable, PillarPage,
  type BarItem, type Figure,
} from '../../components/pillar'
import { Badge, Card, Skeleton } from '../../components/ui'
import { useT } from '../../i18n'
import ProvenanceBadge from '../ProvenanceBadge'
import type { DataProvenance } from '../types'
import './energy.css'

interface Measurements {
  wave_height_m: number | null
  wave_period_s: number | null
  swell_height_m: number | null
  swell_period_s: number | null
  wind_speed_kmh: number | null
  wind_gusts_kmh: number | null
  observed_at: string | null
}
interface Resource {
  wave_power_kw_per_m: number | null
  wind_power_w_per_m2: number | null
  wind_speed_ms: number | null
  period_basis: string
  wind_height_basis: string
}
interface Assessment {
  site_id: string; name: string; region: string; exposure: string
  nearshore: boolean; approx_distance_from_shore_km: number
  measurements: Measurements; resource: Resource; interpretation: string
}
interface EnergyBrief {
  provenance: DataProvenance
  sites: Assessment[]
  comparison: Array<{ site_id: string; wave_power_kw_per_m: number | null }>
  assessment_basis: string
  formulas: Record<string, string>
}

export default function EnergySurface() {
  const t = useT()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['energy-resource'],
    queryFn: () => api.energyResource().then((r) => r as unknown as EnergyBrief),
    retry: 0,
  })

  if (isLoading) return <Card><Skeleton text count={3} /></Card>
  if (isError || !data) {
    return <Card title={t('energy.title')}><p>{t('energy.unavailable')}</p></Card>
  }

  const rank = new Map(data.comparison.map((c, i) => [c.site_id, i + 1]))
  const ordered = [...data.sites].sort(
    (a, b) => (rank.get(a.site_id) ?? 99) - (rank.get(b.site_id) ?? 99))

  const best = ordered[0]
  const bestPower = best?.resource.wave_power_kw_per_m ?? null

  // --- 1. Answer. Hero is the same value the sentence quotes. -------------
  const sentence = bestPower != null
    ? t('energy.answerLead')
      .replace('{site}', best.name)
      .replace('{value}', String(bestPower))
    : t('energy.answerNoData')

  // --- 2. Figures ---------------------------------------------------------
  const figures: Figure[] = best ? [
    {
      label: t('energy.wavePower'),
      value: best.resource.wave_power_kw_per_m,
      unit: 'kW/m',
      note: t('energy.figureBestSite'),
    },
    {
      label: t('energy.windPower'),
      value: best.resource.wind_power_w_per_m2,
      unit: 'W/m²',
      note: t('energy.figureAt10m'),
    },
    {
      label: t('energy.distanceFromShore'),
      value: best.approx_distance_from_shore_km,
      unit: 'km',
      note: best.nearshore ? t('energy.figureNearshore') : undefined,
    },
    {
      label: t('energy.swellPeriod'),
      value: best.measurements.swell_period_s,
      unit: 's',
    },
  ] : []

  // --- 3. Visual ----------------------------------------------------------
  const bars: BarItem[] = ordered.map((s) => ({
    id: s.site_id,
    label: s.name,
    value: s.resource.wave_power_kw_per_m,
    unit: 'kW/m',
    detail: `${s.region} · ~${s.approx_distance_from_shore_km} km ${t('energy.offshore')}`,
    highlight: s.site_id === best?.site_id,
  }))

  return (
    <PillarPage
      title={t('energy.title')}
      answer={
        <Answer
          sentence={sentence}
          hero={bestPower != null
            ? { value: bestPower, unit: 'kW/m', caption: t('energy.heroCaption') }
            : undefined}
        />
      }
      figures={<FigureRow figures={figures} unavailableLabel={t('energy.unavailableShort')} />}
      chips={<ProvenanceBadge provenance={data.provenance} compact />}
      visual={
        <BarComparison
          items={bars}
          caption={t('energy.barCaption')}
          unavailableLabel={t('energy.unavailableShort')}
        />
      }
      detail={
        <Foldable
          title={t('energy.detailTitle')}
          hint={t('energy.detailHint').replace('{n}', String(ordered.length))}
        >
          <div className="ene-detail-list">
            {ordered.map((site) => {
              const { measurements: m, resource: r } = site
              return (
                <section key={site.site_id} className="ene-detail">
                  <h4 className="ene-detail__head">
                    <span className="ene-rank ene-data">#{rank.get(site.site_id)}</span>
                    {site.name}
                    {site.nearshore && <Badge tone="warning">{t('energy.nearshore')}</Badge>}
                  </h4>
                  <p className="ene-exposure">{site.exposure}</p>

                  <div className="ene-resource-grid">
                    <div className="ene-resource">
                      <h5><Waves size={16} aria-hidden="true" /> {t('energy.wavePower')}</h5>
                      <p className="ene-value ene-data">
                        {r.wave_power_kw_per_m ?? '—'}<span className="ene-unit"> kW/m</span>
                      </p>
                      {/* Inputs substituted so the figure can be re-derived by hand. */}
                      <p className="ene-derivation ene-data">
                        0.49 × ({m.wave_height_m ?? '—'} m)² × {m.wave_period_s ?? '—'} s
                      </p>
                    </div>
                    <div className="ene-resource">
                      <h5><Wind size={16} aria-hidden="true" /> {t('energy.windPower')}</h5>
                      <p className="ene-value ene-data">
                        {r.wind_power_w_per_m2 ?? '—'}<span className="ene-unit"> W/m²</span>
                      </p>
                      <p className="ene-derivation ene-data">
                        0.5 × 1.225 × ({m.wind_speed_kmh ?? '—'} km/h ÷ 3.6 = {r.wind_speed_ms ?? '—'} m/s)³
                      </p>
                    </div>
                  </div>

                  {site.interpretation ? (
                    <div className="ene-interpretation">
                      <p>{site.interpretation}</p>
                      <p className="ene-interpretation__note">{t('energy.interpretationNote')}</p>
                    </div>
                  ) : (
                    <p className="ene-no-interpretation">{t('energy.noInterpretation')}</p>
                  )}
                </section>
              )
            })}
          </div>
        </Foldable>
      }
      method={
        <Foldable title={t('energy.formulasTitle')} tone="method">
          <ul className="ene-data ene-formula-list">
            {Object.entries(data.formulas).map(([k, v]) => (
              <li key={k}><strong>{k}</strong>: {v}</li>
            ))}
          </ul>
          <p className="ene-formulas__note">{t('energy.formulasNote')}</p>
        </Foldable>
      }
      limits={
        <Foldable title={t('energy.limitsTitle')} tone="limits">
          {/* Verbatim from the backend — never paraphrased into something weaker. */}
          <p>{data.assessment_basis}</p>
          {best && (
            <ul className="ene-limits">
              {best.nearshore && <li>{t('energy.limitNearshore')}</li>}
              <li>{best.resource.period_basis}</li>
              <li>{best.resource.wind_height_basis}</li>
            </ul>
          )}
          <p className="ene-coverage">{data.provenance.coverage_note}</p>
        </Foldable>
      }
    />
  )
}
