/**
 * Pagination — FROZEN.
 * Props:
 *   page      number  1-based current page
 *   pageCount number
 *   onChange  (page: number) => void
 *   label?    string  what is being paged (default 'results')
 *
 * Deliberately simple: previous / status / next. The status line is the
 * accessible source of truth and is announced politely on change.
 */
import { ChevronLeft, ChevronRight } from 'lucide-react'

export function Pagination({ page, pageCount, onChange, label = 'results' }: {
  page: number; pageCount: number; onChange: (page: number) => void; label?: string
}) {
  if (pageCount <= 1) return null
  return (
    <nav className="lk-pagination" aria-label={`${label} pagination`}>
      <button type="button" className="lk-btn lk-btn--secondary"
        onClick={() => onChange(page - 1)} disabled={page <= 1}>
        <ChevronLeft size={18} aria-hidden="true" />Previous
      </button>
      <span className="lk-pagination__status" aria-live="polite">Page {page} of {pageCount}</span>
      <button type="button" className="lk-btn lk-btn--secondary"
        onClick={() => onChange(page + 1)} disabled={page >= pageCount}>
        Next<ChevronRight size={18} aria-hidden="true" />
      </button>
    </nav>
  )
}
