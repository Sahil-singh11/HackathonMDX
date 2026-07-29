/* Catch detail sheet (Lane B).
 *
 * Focus is trapped while open, Escape closes, and focus returns to the row that
 * opened it. Phase 0 will provide a shared Sheet primitive; when it lands this
 * should be re-expressed as a wrapper around it rather than its own dialog.
 *
 * Props:
 *   record     CatchRow | null   null closes the sheet
 *   onClose    () => void
 *   onEdit     (id: string) => void   correct the species on this record
 */
import { PencilLine, X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useT } from '../../i18n'
import type { CatchRow } from './types'

interface Props {
  record: CatchRow | null
  speciesLabel: (id: string) => string
  onClose: () => void
  onEdit: (id: string) => void
}

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'

export default function CatchDetailSheet({ record, speciesLabel, onClose, onEdit }: Props) {
  const panelRef = useRef<HTMLDivElement>(null)
  const returnFocusRef = useRef<HTMLElement | null>(null)
  const t = useT()

  useEffect(() => {
    if (!record) return
    returnFocusRef.current = document.activeElement as HTMLElement
    const panel = panelRef.current
    panel?.querySelector<HTMLElement>(FOCUSABLE)?.focus()

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key !== 'Tab' || !panel) return
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE))
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }

    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      returnFocusRef.current?.focus()
    }
  }, [record, onClose])

  if (!record) return null

  const rows: Array<[string, React.ReactNode]> = [
    [t('log.detail.species'), speciesLabel(record.species_id)],
    [t('log.detail.date'), <span className="mono" key="d">{record.capture_date}</span>],
    [t('log.detail.length'), record.measured_length_cm != null
      ? <span className="mono" key="l">{record.measured_length_cm} cm</span>
      : <span key="l">{t('log.detail.notMeasured')}</span>],
    [t('log.detail.count'), <span className="mono" key="c">{record.count}</span>],
    [t('log.detail.area'), record.fishing_area || t('log.detail.noArea')],
    [t('log.detail.status'), t(`catch.rule.${record.legal_status}`)],
    [t('log.detail.recordId'), <span className="mono truncate" key="i">{record.id}</span>],
  ]

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div ref={panelRef} className="sheet-panel" role="dialog" aria-modal="true"
        aria-labelledby="sheet-title" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <h2 id="sheet-title">{speciesLabel(record.species_id)}</h2>
          <button type="button" className="sheet-close" onClick={onClose} aria-label={t('common.close')}>
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <dl className="detail-list">
          {rows.map(([label, value]) => (
            <div className="detail-row" key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>

        <button type="button" className="secondary" onClick={() => onEdit(record.id)}>
          <PencilLine size={16} aria-hidden="true" /> {t('log.detail.correctSpecies')}
        </button>

        <p className="banner warn">{t('catch.rule.verify')}</p>
      </div>
    </div>
  )
}
