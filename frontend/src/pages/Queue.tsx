import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'
import { listQueue, removeFromQueue, type QueuedCatch } from '../utils/idb'

export default function Queue() {
  const t = useT()
  const online = useAppStore((s) => s.online)
  const qc = useQueryClient()
  const [local, setLocal] = useState<QueuedCatch[]>([])
  const { data: server } = useQuery({ queryKey: ['syncQueue'], queryFn: api.syncQueue })

  const refreshLocal = () => listQueue().then(setLocal).catch(() => setLocal([]))
  useEffect(() => { refreshLocal() }, [])

  const syncMut = useMutation({
    mutationFn: async () => {
      for (const item of await listQueue()) {
        await api.createCatch({
          confirmed_species_id: item.species_id,
          measured_length_cm: item.measured_length_cm,
          count: item.count,
          capture_date: item.capture_date,
          fishing_area: item.fishing_area,
        })
        if (item.id != null) await removeFromQueue(item.id)
      }
      await api.processSync()
    },
    onSuccess: () => {
      refreshLocal()
      qc.invalidateQueries({ queryKey: ['catches'] })
      qc.invalidateQueries({ queryKey: ['syncQueue'] })
      qc.invalidateQueries({ queryKey: ['reportToday'] })
    },
  })

  const total = local.length + (server?.queued ?? 0)

  return (
    <div className="card">
      <h2>{t('queue.title')}</h2>
      {!online && <p className="banner warn">{t('common.offline')}</p>}
      {total === 0 && <p className="small">{t('queue.empty')}</p>}
      {local.map((item) => (
        <div className="list-row" key={`local-${item.id}`}>
          <div>
            <strong>{item.species_id}</strong> × {item.count}
            <div className="sub">{item.capture_date}{item.measured_length_cm ? ` · ${item.measured_length_cm} cm` : ''} · device</div>
          </div>
          <span className="badge offline">{t('queue.queued')}</span>
        </div>
      ))}
      {(server?.items ?? []).filter((i) => i.status === 'queued').map((i) => (
        <div className="list-row" key={String(i.id)}>
          <div><strong>{String(i.kind)}</strong><div className="sub">server</div></div>
          <span className="badge offline">{t('queue.queued')}</span>
        </div>
      ))}
      {total > 0 && (
        <button className="primary" disabled={!online || syncMut.isPending} onClick={() => syncMut.mutate()}>
          {t('queue.process')}
        </button>
      )}
      {syncMut.isError && <p className="banner danger">{t('common.error')}</p>}
    </div>
  )
}
