/**
 * Chip — FROZEN. A toggleable filter/tag control.
 * Props:
 *   selected  boolean    controlled state
 *   onToggle  () => void
 *   icon?     ReactNode
 *   disabled? boolean
 *   children  ReactNode  the label (required — no icon-only chips)
 *
 * Selected state is conveyed by aria-pressed AND a check glyph AND colour, so
 * it survives colour-blindness and greyscale printing.
 */
import { Check } from 'lucide-react'
import type { ReactNode } from 'react'

export function Chip({ selected, onToggle, icon, disabled, children }: {
  selected: boolean; onToggle: () => void; icon?: ReactNode; disabled?: boolean; children: ReactNode
}) {
  return (
    <button type="button" className="lk-chip" aria-pressed={selected} disabled={disabled} onClick={onToggle}>
      {selected ? <Check size={18} aria-hidden="true" /> : icon}
      {children}
    </button>
  )
}
