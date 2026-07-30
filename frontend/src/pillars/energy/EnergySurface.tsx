/* Workstream 2 — Ocean-Based Renewable Energy surface.
 *
 * The design job here is to stop a resource indication from reading as a yield
 * study. So:
 *   - the formula is printed next to the figure it produced, with the inputs, so
 *     a reader can re-derive it rather than trusting it
 *   - the "not a yield assessment / not a survey" basis sits above the numbers,
 *     not in a footer
 *   - the period and hub-height caveats attach to the specific figures they
 *     qualify, not to a general disclaimer nobody reads
 *   - model prose is visually separated and labelled as unable to change a figure
 */
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Bot, Calculator, Info, Waves, Wind } from 'lucide-react'
import { api } from '../../api/client'
import { Badge, Card, Skeleton } from '../../components/ui'
import { useT } from '../../i18n'
import ProvenanceBadge from '../ProvenanceBadge'
import type { DataProvenance } from '../types'
import './energy.css'

/** Rungs that mean "a language model wrote these sentences". */
const MODEL_RUNGS = new Set(['model', 'cached'])

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
  /* 'model' | 'deterministic_fallback'. The backend now always fills
   * `interpretation` — with a mechanical summary when the model is unusable — so
   * presence alone no longer means a model wrote it. This field is the only way
   * to tell, and mislabelling assembled text as model reasoning (or vice versa)
   * is exactly the overclaim the pillar is meant to avoid. */
  interpretation_source: string
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

  return (
    <div className="ene-surface">
      <Card title={t('energy.title')}>
        <p className="ene-intro">{t('energy.intro')}</p>

        {/* Above the numbers, deliberately. */}
        <p className="ene-basis" role="note">
          <AlertTriangle size={18} aria-hidden="true" />
          <span>{data.assessment_basis}</span>
        </p>

        <div className="ene-formulas">
          <h4><Calculator size={16} aria-hidden="true" /> {t('energy.formulasTitle')}</h4>
          <ul className="ene-data">
            {Object.entries(data.formulas).map(([k, v]) => (
              <li key={k}><strong>{k}</strong>: {v}</li>
            ))}
          </ul>
          <p className="ene-formulas__note">{t('energy.formulasNote')}</p>
        </div>

        <ProvenanceBadge provenance={data.provenance} />
      </Card>

      {ordered.map((site) => {
        const { measurements: m, resource: r } = site
        return (
          <Card
            key={site.site_id}
            title={
              <span className="ene-site-title">
                <span className="ene-rank ene-data">#{rank.get(site.site_id)}</span>
                {site.name}
              </span>
            }
            action={site.nearshore && (
              <Badge tone="warning" icon={<AlertTriangle size={14} aria-hidden="true" />}>
                {t('energy.nearshore')}
              </Badge>
            )}
          >
            <p className="ene-exposure">{site.exposure}</p>
            <p className="ene-distance ene-data">
              ~{site.approx_distance_from_shore_km} km {t('energy.offshore')}
            </p>

            <div className="ene-resource-grid">
              {/* Each figure shows its own inputs so it can be re-derived. */}
              <div className="ene-resource">
                <h4><Waves size={16} aria-hidden="true" /> {t('energy.wavePower')}</h4>
                <p className="ene-value ene-data">
                  {r.wave_power_kw_per_m ?? '—'}<span className="ene-unit"> kW/m</span>
                </p>
                <p className="ene-derivation ene-data">
                  0.49 × ({m.wave_height_m ?? '—'} m)² × {m.wave_period_s ?? '—'} s
                </p>
                <p className="ene-caveat">
                  <Info size={14} aria-hidden="true" /> {r.period_basis}
                </p>
              </div>

              <div className="ene-resource">
                <h4><Wind size={16} aria-hidden="true" /> {t('energy.windPower')}</h4>
                <p className="ene-value ene-data">
                  {r.wind_power_w_per_m2 ?? '—'}<span className="ene-unit"> W/m²</span>
                </p>
                <p className="ene-derivation ene-data">
                  0.5 × 1.225 × ({m.wind_speed_kmh ?? '—'} km/h ÷ 3.6 = {r.wind_speed_ms ?? '—'} m/s)³
                </p>
                <p className="ene-caveat">
                  <Info size={14} aria-hidden="true" /> {r.wind_height_basis}
                </p>
              </div>
            </div>

            {/* Same two-state treatment as TransportSurface, on purpose: one
                pattern for "who wrote this sentence" across the platform. */}
            {site.interpretation && (
              <div className="ene-interpretation">
                <h4>{t('energy.interpretation')}</h4>
                {/* 'cached' IS model prose — the same sentences, already checked by
                    the envelope guard and the number firewall before they were
                    stored, reused instead of paying for an identical second call.
                    Rendering it under a "Mechanical summary" badge would be a
                    plain misattribution, so both rungs get the model badge and
                    only the reuse note distinguishes them. */}
                {MODEL_RUNGS.has(site.interpretation_source) ? (
                  <Badge tone="accent" icon={<Bot size={14} aria-hidden="true" />}>
                    {t('transport.sourceModel')}
                  </Badge>
                ) : (
                  <Badge tone="neutral" icon={<Calculator size={14} aria-hidden="true" />}>
                    {t('transport.sourceMechanical')}
                  </Badge>
                )}
                <p>{site.interpretation}</p>
                {site.interpretation_source === 'cached' && (
                  <p className="ene-interpretation__note">{t('pillars.narrativeReused')}</p>
                )}
                {MODEL_RUNGS.has(site.interpretation_source) && (
                  <p className="ene-interpretation__note">{t('energy.interpretationNote')}</p>
                )}
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}
