/**
 * Table — FROZEN. Sortable, and collapses to cards under 768px.
 *
 * Props:
 *   columns   Column<T>[]   { key, header, sortable?, align?, data?, render? }
 *                           data: true renders the cell in the mono role
 *   rows      T[]
 *   rowKey    (row: T) => string
 *   caption   string        required — describes the table for screen readers
 *   onRowClick? (row: T) => void   adds a keyboard-reachable row action
 *   empty?    ReactNode     shown instead of an empty tbody
 *   initialSort? { key, dir }
 *
 * Sorting is client-side and stable. Each <td> carries data-label so the
 * card view under 768px still shows which column a value belongs to.
 *
 * Row click: when onRowClick is given, each row also renders a real button in
 * the first cell so the action is reachable by keyboard — a click handler on
 * <tr> alone is not accessible.
 */
import { useMemo, useState, type ReactNode } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'

export interface Column<T> {
  key: string
  header: string
  sortable?: boolean
  align?: 'left' | 'right'
  data?: boolean
  render?: (row: T) => ReactNode
  /** Value used for sorting; defaults to the raw field at `key`. */
  sortValue?: (row: T) => string | number
}

type Dir = 'asc' | 'desc'

export function Table<T extends Record<string, unknown>>({
  columns, rows, rowKey, caption, onRowClick, empty, initialSort,
}: {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  caption: string
  onRowClick?: (row: T) => void
  empty?: ReactNode
  initialSort?: { key: string; dir: Dir }
}) {
  const [sort, setSort] = useState<{ key: string; dir: Dir } | null>(initialSort ?? null)

  const sorted = useMemo(() => {
    if (!sort) return rows
    const col = columns.find((c) => c.key === sort.key)
    if (!col) return rows
    const get = col.sortValue ?? ((r: T) => r[sort.key] as string | number)
    return [...rows].sort((a, b) => {
      const av = get(a), bv = get(b)
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av ?? '').localeCompare(String(bv ?? ''))
      return sort.dir === 'asc' ? cmp : -cmp
    })
  }, [rows, sort, columns])

  const toggle = (key: string) =>
    setSort((s) => (s?.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }))

  if (rows.length === 0 && empty) return <>{empty}</>

  return (
    <div className="lk-table-wrap">
      <table className="lk-table lk-table--cards">
        <caption className="lk-sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((c) => {
              const active = sort?.key === c.key
              return (
                <th key={c.key} scope="col" style={{ textAlign: c.align ?? 'left' }}
                  aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : undefined}>
                  {c.sortable ? (
                    <button type="button" className="lk-table__sort" onClick={() => toggle(c.key)}>
                      {c.header}
                      {active
                        ? (sort.dir === 'asc' ? <ArrowUp size={14} aria-hidden="true" /> : <ArrowDown size={14} aria-hidden="true" />)
                        : <ArrowUpDown size={14} aria-hidden="true" />}
                      <span className="lk-sr-only">
                        {active ? `sorted ${sort.dir === 'asc' ? 'ascending' : 'descending'}` : 'not sorted'}
                      </span>
                    </button>
                  ) : c.header}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c, ci) => (
                <td key={c.key} data-label={c.header}
                  className={c.data ? 'lk-data' : undefined}
                  style={{ textAlign: c.align ?? 'left' }}>
                  {ci === 0 && onRowClick ? (
                    <button type="button" className="lk-btn lk-btn--ghost" onClick={() => onRowClick(row)}>
                      {c.render ? c.render(row) : String(row[c.key] ?? '')}
                    </button>
                  ) : (
                    c.render ? c.render(row) : String(row[c.key] ?? '')
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
