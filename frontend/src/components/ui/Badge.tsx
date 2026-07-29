/**
 * Badge — FROZEN.
 * Props:
 *   tone?  'neutral' | 'accent' | 'success' | 'warning' | 'danger' (default 'neutral')
 *   icon?  ReactNode — include one where the badge carries meaning, so colour
 *          is never the only signal.
 *   children ReactNode
 */
import type { ReactNode } from 'react'

export type BadgeTone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger'

export function Badge({ tone = 'neutral', icon, children }: {
  tone?: BadgeTone; icon?: ReactNode; children: ReactNode
}) {
  return <span className={`lk-badge lk-badge--${tone}`}>{icon}{children}</span>
}
