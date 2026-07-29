import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'

export default function Declaration() {
  const t = useT()
  const { profileName, fishingArea } = useAppStore()
  const today = new Date().toISOString().slice(0, 10)
  const monthStart = today.slice(0, 8) + '01'
  const [start, setStart] = useState(monthStart)
  const [end, setEnd] = useState(today)
  const [draft, setDraft] = useState<Record<string, unknown> | null>(null)
  const [receipt, setReceipt] = useState<Record<string, unknown> | null>(null)

  const prepareMut = useMutation({
    mutationFn: () => api.prepareDeclaration({
      fisher_name: profileName, fishing_area: fishingArea, period_start: start, period_end: end,
    }),
    onSuccess: setDraft,
  })
  const submitMut = useMutation({
    mutationFn: () => api.mockSubmit(String(draft?.declaration_id)),
    onSuccess: setReceipt,
  })

  const catches = (draft?.catches as Record<string, unknown>[] | undefined) ?? []

  return (
    <>
      <div className="card">
        <h2>{t('decl.title')}</h2>
        <p className="small">{t('decl.subtitle')}</p>
        <p className="banner danger"><strong>{t('decl.mockWarning')}</strong></p>
        <label className="field">{t('decl.periodStart')}
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="field">{t('decl.periodEnd')}
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <button className="primary" disabled={prepareMut.isPending} onClick={() => prepareMut.mutate()}>
          {t('decl.prepare')}
        </button>
        {prepareMut.isError && <p className="banner danger">{t('common.error')}</p>}
      </div>

      {draft && (
        <div className="card">
          <h3>{String(draft.mock_label)}</h3>
          {catches.length === 0 && <p className="small">{t('history.empty')}</p>}
          {catches.map((c, i) => (
            <div className="list-row" key={i}>
              <div><strong>{String(c.species_id)}</strong> × {String(c.count)}
                <div className="sub">{String(c.capture_date)}{c.measured_length_cm ? ` · ${c.measured_length_cm} cm` : ''}</div>
              </div>
              <span className={`legal-${String(c.legal_status)}`}>{String(c.legal_status)}</span>
            </div>
          ))}
          <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.7rem', flexWrap: 'wrap' }}>
            <a className="primary" style={{ flex: 1 }}
              href={`/api/declarations/${String(draft.declaration_id)}/pdf`} target="_blank" rel="noreferrer">
              {t('decl.pdf')}
            </a>
            <button className="secondary" style={{ flex: 1 }} disabled={submitMut.isPending}
              onClick={() => submitMut.mutate()}>
              {t('decl.submitMock')}
            </button>
          </div>
        </div>
      )}

      {receipt && (
        <div className="card">
          <h3>{t('decl.receipt')}</h3>
          <p className="mono" style={{ fontSize: '1.2rem' }}>{String(receipt.mock_receipt_id)}</p>
          <p className="banner mockline">{String(receipt.notice)}</p>
        </div>
      )}
    </>
  )
}
