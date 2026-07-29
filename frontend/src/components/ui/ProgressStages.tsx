/**
 * ProgressStages — FROZEN.
 * Props:
 *   stages   string[]  ordered stage names — use REAL stage names, not fake ones
 *   current  number    index of the active stage; stages before it read as done
 *   done?    boolean   all stages complete
 *
 * Honest progress only. If the underlying work reports no granular phases, say
 * so in a comment where you use this rather than implying telemetry you do not have.
 */
import { Check } from 'lucide-react'

export function ProgressStages({ stages, current, done }: {
  stages: string[]; current: number; done?: boolean
}) {
  return (
    <ol className="lk-stages" aria-live="polite">
      {stages.map((s, i) => {
        const isDone = done || i < current
        const isActive = !done && i === current
        return (
          <li key={s} className={`lk-stage${isActive ? ' lk-stage--active' : ''}${isDone ? ' lk-stage--done' : ''}`}>
            {isDone ? <Check size={14} aria-hidden="true" /> : <span className="lk-stage__dot" aria-hidden="true" />}
            {s}
            <span className="lk-sr-only">{isDone ? ' complete' : isActive ? ' in progress' : ' pending'}</span>
          </li>
        )
      })}
    </ol>
  )
}
