import { useQuery } from '@tanstack/react-query'
import Compass from '../components/Compass'
import { useT } from '../i18n'
import { api } from '../api/client'

/**
 * Sea conditions.
 *
 * LAYOUT. This page is seven metric tiles plus a compass, which is why it opts
 * into the shell's `wide` variant (App.tsx WIDE_ROUTES) instead of the 960px
 * reading column: at 960px the shared 2-column .stat-grid wrapped the tiles
 * 2/2/2/1, leaving an orphan tile and a large dead area beside it. The grid is
 * now auto-fit, so the tiles use whatever width the viewport gives them.
 *
 * THE MARINE DISCLAIMER IS STILL HERE, and deliberately. It used to sit below
 * the card as a yellow warning banner; that treatment is gone, because a standing
 * caveat styled as a warning reads as an error state on a page that is working
 * normally. The sentence itself is safety-critical — it mirrors MARINE_DISCLAIMER
 * in backend/app/core/limitations.py and is row 1 of
 * docs/MORISYEN_HUMAN_REVIEW.md ("Safety-critical marine wording") — so it stays,
 * in the card footer beside the attribution, where the source and the caveat are
 * read together. Deleting it outright would strip a safety disclosure from the
 * page fishers use to decide whether to go out.
 */
export default function Marine() {
  const t = useT()
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['marine'], queryFn: api.marine })

  if (isLoading) return <p role="status">{t('common.loading')}</p>
  if (isError || !data) {
    return (
      <div className="card">
        <p className="banner danger">{t('common.error')}</p>
        <button className="secondary" onClick={() => refetch()}>{t('common.retry')}</button>
      </div>
    )
  }

  const num = (v: unknown) => (typeof v === 'number' ? v : null)
  const display = (v: unknown) => (typeof v === 'number' ? v : '—')
  const stats = [
    { label: t('marine.waveHeight'), value: display(data.wave_height_m), unit: 'm' },
    { label: t('marine.waveDirection'), value: display(data.wave_direction_deg), unit: '°' },
    { label: t('marine.wavePeriod'), value: display(data.wave_period_s), unit: 's' },
    { label: t('marine.swellHeight'), value: display(data.swell_height_m), unit: 'm' },
    { label: t('marine.swellDirection'), value: display(data.swell_direction_deg), unit: '°' },
    { label: t('marine.swellPeriod'), value: display(data.swell_period_s), unit: 's' },
    { label: t('marine.sst'), value: display(data.sea_surface_temperature_c), unit: '°C' },
  ]

  return (
    <div className="card marine-card">
      <div className="marine-head">
        <h2>{t('marine.title')}</h2>
        <div className="marine-badges">
          {Boolean(data.mock) && <span className="badge mock">{t('common.provider.mock')}</span>}
          {Boolean(data.stale) && <span className="badge offline">{t('marine.stale')}</span>}
        </div>
      </div>

      <div className="marine-layout">
        <Compass waveDeg={num(data.wave_direction_deg)} swellDeg={num(data.swell_direction_deg)}
          waveLabel={t('marine.waveDirection')} swellLabel={t('marine.swellDirection')} />
        <div className="stat-grid">
          {stats.map((s) => (
            <div className="stat" key={s.label}>
              <div className="label">{s.label}</div>
              <div className="value">{String(s.value)}<span className="unit">{s.unit}</span></div>
            </div>
          ))}
        </div>
      </div>

      {/* Source and caveat together: where the numbers came from, and what they
          do not promise. See the note at the top of this file. */}
      <footer className="marine-footer">
        <p className="caption">
          {t('marine.source')}: {String(data.attribution ?? data.source)} · {t('marine.updated')}: {String(data.time ?? '—')}
        </p>
        <p className="caption marine-caveat">{t('marine.disclaimer')}</p>
      </footer>
    </div>
  )
}
