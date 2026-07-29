import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useT } from '../i18n'

export default function DemoControls() {
  const t = useT()
  const qc = useQueryClient()
  const [date, setDate] = useState('2026-09-01')
  const [msg, setMsg] = useState('')

  const setMut = useMutation({
    mutationFn: () => api.setDemoDate(date),
    onSuccess: () => { setMsg(`${t('common.simulatedDate')}: ${date}`); qc.invalidateQueries() },
  })
  const resetMut = useMutation({
    mutationFn: api.demoReset,
    onSuccess: () => { setMsg('reset ✓'); qc.invalidateQueries() },
  })

  return (
    <div className="card">
      <h2>{t('demo.title')}</h2>
      <p className="small">{t('demo.note')}</p>
      <label className="field">{t('demo.setDate')}
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </label>
      <button className="primary" disabled={setMut.isPending} onClick={() => setMut.mutate()}>
        {t('demo.setDate')}
      </button>
      <div style={{ height: '0.6rem' }} />
      <button className="secondary" disabled={resetMut.isPending} onClick={() => resetMut.mutate()}>
        {t('demo.clear')}
      </button>
      {msg && <p className="banner info" role="status">{msg}</p>}
    </div>
  )
}
