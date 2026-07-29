import { useQuery } from '@tanstack/react-query'
import { BookOpen, Camera, CloudOff } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import CatchDetailSheet from '../components/log/CatchDetailSheet'
import LogFilters, { type FilterState } from '../components/log/LogFilters'
import '../components/log/log.css'
import { toCatchRow, type CatchRow } from '../components/log/types'
import { useT } from '../i18n'
import { listQueue } from '../utils/idb'

const PAGE_SIZE = 50
const EMPTY_FILTERS: FilterState = { from: '', to: '', speciesId: '', sync: 'all' }

export default function History() {
  const t = useT()
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const [visible, setVisible] = useState(PAGE_SIZE)
  const [selected, setSelected] = useState<CatchRow | null>(null)
  const [queued, setQueued] = useState<CatchRow[]>([])

  const { data, isLoading } = useQuery({ queryKey: ['catches'], queryFn: api.catches })
  const { data: report } = useQuery({ queryKey: ['reportToday'], queryFn: api.reportToday })
  const { data: speciesData } = useQuery({ queryKey: ['species'], queryFn: api.species })

  const speciesById = useMemo(
    () => new Map((speciesData?.species ?? []).map((s) => [s.species_id, s])),
    [speciesData],
  )
  const speciesLabel = (id: string) => speciesById.get(id)?.english ?? id

  // Locally queued records are part of the log — hiding them would misreport
  // what the fisher has actually recorded.
  useEffect(() => {
    listQueue()
      .then((items) => setQueued(items.map((q) => ({
        id: `queued-${q.id ?? q.queued_at}`,
        species_id: q.species_id,
        count: q.count,
        capture_date: q.capture_date,
        measured_length_cm: q.measured_length_cm,
        fishing_area: q.fishing_area,
        legal_status: 'unknown',
        pending: true,
      }))))
      .catch(() => setQueued([]))
  }, [])

  const allRows: CatchRow[] = useMemo(
    () => [...queued, ...(data?.catches ?? []).map(toCatchRow)],
    [queued, data],
  )

  const filtered = useMemo(() => allRows.filter((r) => {
    if (filters.from && r.capture_date < filters.from) return false
    if (filters.to && r.capture_date > filters.to) return false
    if (filters.speciesId && r.species_id !== filters.speciesId) return false
    if (filters.sync === 'pending' && !r.pending) return false
    if (filters.sync === 'synced' && r.pending) return false
    return true
  }), [allRows, filters])

  const grouped = useMemo(() => {
    const byDay = new Map<string, CatchRow[]>()
    for (const row of filtered.slice(0, visible)) {
      const key = row.capture_date || t('log.noDate')
      const list = byDay.get(key) ?? []
      list.push(row)
      byDay.set(key, list)
    }
    return [...byDay.entries()].sort((a, b) => b[0].localeCompare(a[0]))
  }, [filtered, visible, t])

  const pendingCount = allRows.filter((r) => r.pending).length
  const activeFilterCount = Object.entries(filters)
    .filter(([k, v]) => v !== EMPTY_FILTERS[k as keyof FilterState]).length

  const speciesOptions = useMemo(
    () => [...new Set(allRows.map((r) => r.species_id))]
      .map((id) => ({ id, label: speciesLabel(id) })),
    [allRows, speciesById],
  )

  if (isLoading) return <p role="status">{t('common.loading')}</p>

  return (
    <>
      <div className="card">
        <h2>{t('history.title')}</h2>
        <div className="stat-grid">
          <div className="stat">
            <div className="label">{t('history.today')}</div>
            <div className="value mono">{String(report?.total_count ?? 0)}</div>
          </div>
          <div className="stat">
            <div className="label">{t('history.total')}</div>
            <div className="value mono">{allRows.length}</div>
          </div>
          {/* Unsynced gets visual priority — it is the number that can cost a record. */}
          <div className={`stat${pendingCount > 0 ? ' stat-priority' : ''}`}>
            <div className="label">{t('log.unsynced')}</div>
            <div className="value mono">{pendingCount}</div>
            <div className="stat-sub">
              {pendingCount > 0 ? t('log.unsyncedHint') : t('log.allSyncedHint')}
            </div>
          </div>
        </div>
      </div>

      {allRows.length > 0 && (
        <LogFilters value={filters} speciesOptions={speciesOptions} activeCount={activeFilterCount}
          onChange={(patch) => { setFilters((f) => ({ ...f, ...patch })); setVisible(PAGE_SIZE) }}
          onReset={() => setFilters(EMPTY_FILTERS)} />
      )}

      {allRows.length === 0 ? (
        <div className="card log-empty">
          <BookOpen size={40} aria-hidden="true" />
          <h3>{t('log.empty.title')}</h3>
          <p>{t('log.empty.body')}</p>
          <Link to="/catch" className="primary log-empty-action">
            <Camera size={18} aria-hidden="true" /> {t('log.empty.action')}
          </Link>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card log-empty">
          <h3>{t('log.noMatches.title')}</h3>
          <p>{t('log.noMatches.body')}</p>
          <button type="button" className="secondary" onClick={() => setFilters(EMPTY_FILTERS)}>
            {t('log.filter.reset')}
          </button>
        </div>
      ) : (
        <>
          {grouped.map(([day, rows]) => (
            <section key={day} className="log-day">
              <h3 className="log-day-head">
                <span className="mono">{day}</span>
                <span className="log-day-count">{rows.length} {t('log.records')}</span>
              </h3>
              <div className="log-rows">
                {rows.map((row) => (
                  <button key={row.id} type="button" className="log-row"
                    onClick={() => setSelected(row)}>
                    <span className={`log-thumb hue-${row.species_id.length % 3}`} aria-hidden="true">
                      {speciesLabel(row.species_id).slice(0, 2).toUpperCase()}
                    </span>
                    <span className="log-row-main">
                      <span className="log-species">{speciesLabel(row.species_id)}</span>
                      <span className="log-meta mono">
                        ×{row.count}
                        {row.measured_length_cm != null && ` · ${row.measured_length_cm} cm`}
                        {row.fishing_area && ` · ${row.fishing_area}`}
                      </span>
                    </span>
                    <span className="log-row-end">
                      <span className={`badge ${row.pending ? 'sync-pending' : 'sync-synced'}`}>
                        {row.pending && <CloudOff size={12} aria-hidden="true" />}
                        {t(row.pending ? 'log.sync.pending' : 'log.sync.synced')}
                      </span>
                      <span className={`legal-${row.legal_status} log-legal`}>
                        {t(`catch.rule.${row.legal_status}`)}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </section>
          ))}

          {filtered.length > visible && (
            <button type="button" className="secondary load-more"
              onClick={() => setVisible((v) => v + PAGE_SIZE)}>
              {t('log.loadMore')} ({filtered.length - visible})
            </button>
          )}
        </>
      )}

      <CatchDetailSheet record={selected} speciesLabel={speciesLabel}
        onClose={() => setSelected(null)} onEdit={() => setSelected(null)} />

      <p className="banner warn">{t('catch.rule.verify')}</p>
    </>
  )
}
