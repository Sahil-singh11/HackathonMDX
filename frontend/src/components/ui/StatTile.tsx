/**
 * StatTile — FROZEN.
 * Props:
 *   label     string     what the number is
 *   value     ReactNode  the number itself (rendered in the mono data role)
 *   hint?     ReactNode  context line. IMPORTANT: never ship a bare "0" with no
 *                        hint — write what zero means ("nothing waiting to sync").
 *   emphasis? boolean    larger, accent-coloured value (default false)
 *   icon?     ReactNode  decorative
 */
import type { ReactNode } from 'react'

export function StatTile({ label, value, hint, emphasis, icon }: {
  label: string; value: ReactNode; hint?: ReactNode; emphasis?: boolean; icon?: ReactNode
}) {
  return (
    <div className={`lk-stat${emphasis ? ' lk-stat--emphasis' : ''}`}>
      <span className="lk-stat__label">{icon}{label}</span>
      <span className="lk-stat__value">{value}</span>
      {hint ? <span className="lk-stat__hint">{hint}</span> : null}
    </div>
  )
}
