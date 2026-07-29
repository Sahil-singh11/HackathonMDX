/* Collapsible catch-log filters (Lane B).
 *
 * Collapsed by default: on a phone the records matter more than the controls.
 * The trigger reports how many filters are active so collapsing never hides
 * the fact that the list is filtered.
 *
 * Props:
 *   from/to        string           ISO dates, '' means unbounded
 *   speciesId      string           '' means all
 *   sync           SyncFilter
 *   speciesOptions Array<{id,label}>
 *   onChange       (patch) => void
 *   onReset        () => void
 */
import { SlidersHorizontal } from 'lucide-react'
import { useState } from 'react'
import { useT } from '../../i18n'
import type { SyncFilter } from './types'

export interface FilterState {
  from: string
  to: string
  speciesId: string
  sync: SyncFilter
}

interface Props {
  value: FilterState
  speciesOptions: Array<{ id: string; label: string }>
  activeCount: number
  onChange: (patch: Partial<FilterState>) => void
  onReset: () => void
}

export default function LogFilters({ value, speciesOptions, activeCount, onChange, onReset }: Props) {
  const t = useT()
  const [open, setOpen] = useState(false)

  return (
    <div className="log-filters">
      <button type="button" className="secondary filters-toggle" aria-expanded={open}
        aria-controls="log-filter-panel" onClick={() => setOpen((v) => !v)}>
        <SlidersHorizontal size={16} aria-hidden="true" />
        {t('log.filters')}
        {activeCount > 0 && <span className="filter-count">{activeCount}</span>}
      </button>

      {open && (
        <div id="log-filter-panel" className="filter-panel">
          <div className="filter-grid">
            <label className="field" htmlFor="filter-from">{t('log.filter.from')}
              <input id="filter-from" type="date" value={value.from}
                onChange={(e) => onChange({ from: e.target.value })} />
            </label>
            <label className="field" htmlFor="filter-to">{t('log.filter.to')}
              <input id="filter-to" type="date" value={value.to}
                onChange={(e) => onChange({ to: e.target.value })} />
            </label>
            <label className="field" htmlFor="filter-species">{t('log.filter.species')}
              <select id="filter-species" value={value.speciesId}
                onChange={(e) => onChange({ speciesId: e.target.value })}>
                <option value="">{t('log.filter.allSpecies')}</option>
                {speciesOptions.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </label>
            <label className="field" htmlFor="filter-sync">{t('log.filter.sync')}
              <select id="filter-sync" value={value.sync}
                onChange={(e) => onChange({ sync: e.target.value as SyncFilter })}>
                <option value="all">{t('log.filter.allSync')}</option>
                <option value="synced">{t('log.sync.synced')}</option>
                <option value="pending">{t('log.sync.pending')}</option>
              </select>
            </label>
          </div>
          {activeCount > 0 && (
            <button type="button" className="secondary" onClick={onReset}>{t('log.filter.reset')}</button>
          )}
        </div>
      )}
    </div>
  )
}
