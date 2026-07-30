/* Collapsible — the shared mechanism behind PillarDetail, PillarMethod and
 * PillarLimits. Internal to this module; not exported from the barrel, because a
 * page author should reach for the three named containers, which carry the right
 * heading and the right default state for their content.
 *
 * Props
 *   title       string     the trigger's heading. Always visible.
 *   summary?    string     one line shown ON the trigger, visible while collapsed.
 *                          This is what makes a folded section folded rather than
 *                          hidden — PillarLimits requires it.
 *   defaultOpen boolean    initial state only (see below).
 *   icon?       ReactNode  decorative, sits before the title.
 *   children    ReactNode  the panel.
 *
 * WHY <details> AND NOT A DIV WITH aria-expanded. <details>/<summary> is
 * focusable, operable with Enter and Space, exposed as a disclosure to screen
 * readers, and searchable by the browser's find-in-page in most engines — all
 * for free, all impossible to get subtly wrong. The chevron is decorative.
 *
 * WHY defaultOpen IS INITIAL-ONLY. The open state lives in React so the chevron
 * and the panel never disagree, but it is seeded once from the viewport and then
 * belongs to the reader. Recomputing it on resize would slam a section shut
 * under someone who had just opened it — a rotated tablet is not a request to
 * collapse the table you are reading.
 */
import { ChevronRight } from 'lucide-react'
import { useState, type ReactNode } from 'react'

export function Collapsible({ title, summary, defaultOpen, icon, children }: {
  title: string
  summary?: string
  defaultOpen: boolean
  icon?: ReactNode
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <details
      className="lkp-fold"
      open={open}
      /* onToggle fires for clicks, Enter, Space and the find-in-page auto-expand,
         so state follows the element rather than trying to predict it. */
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary className="lkp-fold__trigger">
        <ChevronRight className="lkp-fold__chevron" size={18} aria-hidden="true" />
        <span className="lkp-fold__label">
          <span className="lkp-fold__title">
            {icon}
            {title}
          </span>
          {/* Visible collapsed AND expanded: the caveat is the point, and hiding
              it once opened would make the trigger text look like a lie. */}
          {summary && <span className="lkp-fold__summary">{summary}</span>}
        </span>
      </summary>
      <div className="lkp-fold__panel">{children}</div>
    </details>
  )
}

/**
 * Seed for `defaultOpen`. Read once at mount.
 *
 * 768px is the framework's one breakpoint, matching PillarFigures' two-column
 * switch. Guarded for absent matchMedia so the components stay renderable in a
 * non-browser test environment.
 */
export function isDesktopViewport(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return true
  return window.matchMedia('(min-width: 768px)').matches
}
