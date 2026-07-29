/**
 * EmptyState — FROZEN.
 * Props:
 *   title    string     what this screen is for
 *   body?    ReactNode  one sentence explaining what to do next
 *   icon?    ReactNode  decorative
 *   action?  ReactNode  a single clear next step
 *
 * An empty state is a real screen, not the string "no data". Always tell the
 * fisher what the thing is for and give them one action.
 */
import type { ReactNode } from 'react'

export function EmptyState({ title, body, icon, action }: {
  title: string; body?: ReactNode; icon?: ReactNode; action?: ReactNode
}) {
  return (
    <div className="lk-empty">
      {icon ? <div className="lk-empty__icon" aria-hidden="true">{icon}</div> : null}
      <h2 className="lk-empty__title">{title}</h2>
      {body ? <p className="lk-empty__body">{body}</p> : null}
      {action}
    </div>
  )
}
