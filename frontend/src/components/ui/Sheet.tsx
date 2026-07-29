/**
 * Sheet / Modal — FROZEN.
 *
 * Props:
 *   open      boolean
 *   onClose   () => void
 *   title     string     required — every sheet is labelled for screen readers
 *   children  ReactNode
 *   footer?   ReactNode  action row pinned after the body
 *
 * Behaviour that is baked in and must not be reimplemented per-lane:
 *   - focus moves into the sheet on open, and RETURNS to the trigger on close
 *   - Tab is trapped inside while open
 *   - Escape closes
 *   - backdrop click closes
 *   - body scroll is locked while open
 *   - role="dialog" aria-modal with aria-labelledby wired to the title
 *
 * On mobile it presents as a bottom sheet (thumb-reachable), on >=768px as a
 * centred modal.
 */
import { useCallback, useEffect, useId, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'

const FOCUSABLE = [
  'a[href]', 'button:not([disabled])', 'input:not([disabled])', 'select:not([disabled])',
  'textarea:not([disabled])', '[tabindex]:not([tabindex="-1"])',
].join(',')

export function Sheet({ open, onClose, title, children, footer }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  const restoreRef = useRef<HTMLElement | null>(null)
  const titleId = useId()

  // Remember what had focus so we can give it back on close.
  useEffect(() => {
    if (open) restoreRef.current = document.activeElement as HTMLElement | null
  }, [open])

  const close = useCallback(() => {
    onClose()
    // Restore focus after the panel unmounts.
    window.setTimeout(() => restoreRef.current?.focus?.(), 0)
  }, [onClose])

  useEffect(() => {
    if (!open) return
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    // Move focus in.
    const first = panelRef.current?.querySelector<HTMLElement>(FOCUSABLE)
    ;(first ?? panelRef.current)?.focus()

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return }
      if (e.key !== 'Tab') return
      const nodes = panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE)
      if (!nodes || nodes.length === 0) return
      const list = Array.from(nodes)
      const firstEl = list[0]
      const lastEl = list[list.length - 1]
      if (e.shiftKey && document.activeElement === firstEl) { e.preventDefault(); lastEl.focus() }
      else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); firstEl.focus() }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = prevOverflow
    }
  }, [open, close])

  if (!open) return null

  return (
    <div className="lk-sheet-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) close() }}>
      <div className="lk-sheet" role="dialog" aria-modal="true" aria-labelledby={titleId}
        ref={panelRef} tabIndex={-1}>
        <div className="lk-sheet__header">
          <h2 className="lk-sheet__title" id={titleId}>{title}</h2>
          <button type="button" className="lk-btn lk-btn--ghost" onClick={close} aria-label="Close">
            <X size={20} aria-hidden="true" />
          </button>
        </div>
        {children}
        {footer}
      </div>
    </div>
  )
}
