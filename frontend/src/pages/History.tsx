import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useT } from '../i18n'

export default function History() {
  const t = useT()
  const { data, isLoading } = useQuery({ queryKey: ['catches'], queryFn: api.catches })
  const { data: report } = useQuery({ queryKey: ['reportToday'], queryFn: api.reportToday })

  if (isLoading) return <p role="status">{t('common.loading')}</p>
  const catches = data?.catches ?? []

  return (
    <>
      <div className="card">
        <h2>{t('history.title')}</h2>
        <div className="stat-grid">
          <div className="stat">
            <div className="label">{t('history.today')}</div>
            <div className="value">{String(report?.total_count ?? 0)}</div>
          </div>
          <div className="stat">
            <div className="label">{t('history.total')}</div>
            <div className="value">{catches.length}</div>
          </div>
        </div>
      </div>
      {catches.length === 0 && <p className="small">{t('history.empty')}</p>}
      <div className="catch-grid">
        {catches.map((c) => (
          <div className="card catch-card" key={String(c.id)}>
            <div className="list-row" style={{ border: 0, padding: 0 }}>
              <div>
                <strong>{String(c.species_id)}</strong> × {String(c.count)}
                <div className="sub">{String(c.capture_date)}{c.measured_length_cm ? ` · ${c.measured_length_cm} cm` : ''}{c.fishing_area ? ` · ${c.fishing_area}` : ''}</div>
              </div>
              <span className={`legal-${String(c.legal_status)}`}>{t(`catch.rule.${String(c.legal_status)}`)}</span>
            </div>
          </div>
        ))}
      </div>
      <p className="banner warn">{t('catch.rule.verify')}</p>
    </>
  )
}
