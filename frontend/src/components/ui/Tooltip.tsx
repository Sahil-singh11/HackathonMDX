/**
 * Tooltip — FROZEN.
 * Props: label string, children ReactNode (the trigger)
 *
 * Shown on hover AND focus. Never put essential information here alone — a
 * tooltip is unreachable on touch, so treat it as an enhancement only.
 */
import { useId, useState, type ReactNode } from 'react'

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  const id = useId()
  const [open, setOpen] = useState(false)
  return (
    <span className="lk-tooltip-wrap"
      onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
      <span aria-describedby={id}>{children}</span>
      {open ? <span role="tooltip" id={id} className="lk-tooltip">{label}</span> : null}
    </span>
  )
}
