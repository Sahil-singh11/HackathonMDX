/* PillarDetail — collapsible container for tables and full readings.
 *
 * Props
 *   children   ReactNode   the table, or whatever the full detail is.
 *   title?     string      trigger heading. Default 'Full detail'.
 *   summary?   string      one line on the trigger, e.g. 'All 8 sites'.
 *
 * Collapsed on mobile, open on desktop. On a phone the table is the longest thing
 * on the page and it sits between the reader and the provenance strip; on a
 * desktop there is room and hiding it just adds a click.
 *
 * NAME COLLISION, DELIBERATE. `pillars/PillarDetail.tsx` is the existing ROUTE
 * for /pillars/:id — a page. This is a section container inside a page. The brief
 * named this component PillarDetail and the two live in different folders, so
 * nothing breaks; if a file ever needs both, alias on import.
 *
 * Pass ui/Table as the child rather than a hand-rolled <table>: it is already
 * sortable, captioned, and collapses to cards under 768px, which is exactly where
 * this container is collapsed anyway.
 */
import type { ReactNode } from 'react'
import { Collapsible, isDesktopViewport } from './Collapsible'

export function PillarDetail({ children, title = 'Full detail', summary }: {
  children: ReactNode
  title?: string
  summary?: string
}) {
  return (
    <Collapsible title={title} summary={summary} defaultOpen={isDesktopViewport()}>
      {children}
    </Collapsible>
  )
}
