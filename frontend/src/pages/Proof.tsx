import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'

export default function Proof() {
  const t = useT()
  const { lastProvider, lastTrace } = useAppStore()
  const { data: status } = useQuery({ queryKey: ['providerStatus'], queryFn: api.providerStatus })

  const hosted = status?.hosted as Record<string, unknown> | undefined
  const localP = status?.local as Record<string, unknown> | undefined

  return (
    <>
      <div className="card">
        <h2>{t('proof.title')}</h2>
        <h3>{t('proof.provider')}</h3>
        <div className="list-row">
          <div><strong>Hosted Gemma</strong><div className="sub">{String(hosted?.model ?? '')} · google-genai SDK</div></div>
          <span className={`badge ${hosted?.configured ? 'hosted' : 'mock'}`}>
            {hosted?.configured ? 'configured' : 'no API key'}
          </span>
        </div>
        <div className="list-row">
          <div><strong>Local Gemma (edge)</strong><div className="sub">{String(localP?.note ?? '')}</div></div>
          <span className={`badge ${localP?.loaded ? 'hosted' : 'mock'}`}>
            {localP?.loaded ? 'loaded' : 'not loaded'}
          </span>
        </div>
        <div className="list-row">
          <div><strong>Deterministic mock</strong><div className="sub">offline fallback, always disclosed</div></div>
          <span className="badge mock">available</span>
        </div>
      </div>

      <div className="card">
        <h3>{t('proof.trace')}</h3>
        {lastProvider && (
          <p className="small">
            {t(`common.provider.${lastProvider.mode}`)} · {lastProvider.model || 'none'} ·
            real_inference: {String(lastProvider.real_inference)} · {t('proof.latency')}: {lastProvider.latency_ms} ms
          </p>
        )}
        {lastTrace.length === 0 ? (
          <p className="small">{t('proof.noTrace')}</p>
        ) : (
          <table className="trace-table">
            <thead>
              <tr><th>function</th><th>args</th><th>status</th><th>ms</th><th>action</th></tr>
            </thead>
            <tbody>
              {lastTrace.map((tr, i) => (
                <tr key={i} className="mono">
                  <td>{tr.function}</td>
                  <td>{tr.argument_names.join(', ') || '—'}</td>
                  <td>{tr.result_status}</td>
                  <td>{tr.duration_ms}</td>
                  <td>{tr.final_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="small">Traces show argument names only; values and precise coordinates are never displayed.</p>
      </div>
    </>
  )
}
