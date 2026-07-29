/**
 * Card — FROZEN.
 * Props:
 *   title?    ReactNode  renders a header row
 *   action?   ReactNode  right-aligned control in the header
 *   raised?   boolean    stronger elevation + raised surface (default false)
 *   flush?    boolean    remove padding (for tables/media) (default false)
 *   as?       ElementType wrapper element (default 'section')
 *   children  ReactNode
 */
import type { ElementType, ReactNode } from 'react'

export function Card({
  title, action, raised, flush, as: Tag = 'section', className = '', children,
}: {
  title?: ReactNode; action?: ReactNode; raised?: boolean; flush?: boolean
  as?: ElementType; className?: string; children: ReactNode
}) {
  const cls = `lk-card${raised ? ' lk-card--raised' : ''}${flush ? ' lk-card--flush' : ''}${className ? ` ${className}` : ''}`
  return (
    <Tag className={cls}>
      {(title || action) && (
        <div className="lk-card__header">
          {title ? <h2 className="lk-card__title">{title}</h2> : <span />}
          {action}
        </div>
      )}
      {children}
    </Tag>
  )
}
