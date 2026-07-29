import { useQuery } from '@tanstack/react-query'
import { useT } from '../i18n'
import { api } from '../api/client'

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

  const num = (v: unknown) => (typeof v === 'number' ? v : '—')
  const stats = [
    { label: t('marine.waveHeight'), value: num(data.wave_height_m), unit: 'm' },
    { label: t('marine.waveDirection'), value: num(data.wave_direction_deg), unit: '°' },
    { label: t('marine.wavePeriod'), value: num(data.wave_period_s), unit: 's' },
    { label: t('marine.swellHeight'), value: num(data.swell_height_m), unit: 'm' },
    { label: t('marine.swellDirection'), value: num(data.swell_direction_deg), unit: '°' },
    { label: t('marine.swellPeriod'), value: num(data.swell_period_s), unit: 's' },
    { label: t('marine.sst'), value: num(data.sea_surface_temperature_c), unit: '°C' },
  ]

  return (
    <>
      <div className="card">
        <h2>{t('marine.title')}</h2>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
          {Boolean(data.mock) && <span className="badge mock">{t('common.provider.mock')}</span>}
          {Boolean(data.stale) && <span className="badge offline">{t('marine.stale')}</span>}
        </div>
        <div className="stat-grid">
          {stats.map((s) => (
            <div className="stat" key={s.label}>
              <div className="label">{s.label}</div>
              <div className="value">{String(s.value)}<span className="unit">{s.unit}</span></div>
            </div>
          ))}
        </div>
        <p className="small" style={{ marginTop: '0.6rem' }}>
          {t('marine.source')}: {String(data.attribution ?? data.source)} · {t('marine.updated')}: {String(data.time ?? '—')}
        </p>
      </div>
      <p className="banner warn">{t('marine.disclaimer')}</p>
    </>
  )
}
