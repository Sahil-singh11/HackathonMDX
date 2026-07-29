/**
 * Tabs — FROZEN. Follows the ARIA tabs pattern including arrow-key roving focus.
 * Props:
 *   tabs      { id: string; label: string }[]
 *   active    string   id of the selected tab
 *   onChange  (id: string) => void
 *   children  ReactNode  the active panel's content
 *
 * Renders tablist + tabpanel with correct aria-controls/aria-labelledby wiring.
 * Left/Right arrows move between tabs, Home/End jump to first/last.
 */
import { useRef, type ReactNode } from 'react'

export function Tabs({ tabs, active, onChange, children }: {
  tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void; children: ReactNode
}) {
  const listRef = useRef<HTMLDivElement>(null)

  const onKeyDown = (e: React.KeyboardEvent) => {
    const i = tabs.findIndex((t) => t.id === active)
    let next = -1
    if (e.key === 'ArrowRight') next = (i + 1) % tabs.length
    else if (e.key === 'ArrowLeft') next = (i - 1 + tabs.length) % tabs.length
    else if (e.key === 'Home') next = 0
    else if (e.key === 'End') next = tabs.length - 1
    if (next < 0) return
    e.preventDefault()
    onChange(tabs[next].id)
    listRef.current?.querySelectorAll<HTMLElement>('[role="tab"]')[next]?.focus()
  }

  return (
    <>
      <div className="lk-tabs" role="tablist" ref={listRef} onKeyDown={onKeyDown}>
        {tabs.map((t) => (
          <button key={t.id} type="button" role="tab" className="lk-tab"
            id={`tab-${t.id}`} aria-controls={`panel-${t.id}`}
            aria-selected={t.id === active} tabIndex={t.id === active ? 0 : -1}
            onClick={() => onChange(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${active}`} aria-labelledby={`tab-${active}`} tabIndex={0}>
        {children}
      </div>
    </>
  )
}
