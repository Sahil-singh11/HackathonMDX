/**
 * App shell — FROZEN (Sahil's lane).
 *
 * Exports:
 *   <FisherShell>   header + side nav (>=1024px) + floating bottom tabs, the
 *                   ambient ocean layer, skip link, toast + live regions.
 *                   Used for every fisher route.
 *   <PlainShell>    quiet static chrome for /authority and /verify/:id — NO
 *                   fisher tab bar and NO ambient animation, per the brief.
 *                   Shirish builds the authority top bar inside his own lane
 *                   and drops it in here as `chrome`.
 *   <SkipLink>      first tab stop.
 *
 * The header/nav markup deliberately reuses the EXISTING .topbar / .side-nav /
 * .bottom-nav classes from styles.css rather than restyling them, so the shell
 * gains Phase 0 controls without moving the layout that already shipped.
 */
import { useState, type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Anchor, BookOpen, Camera, Compass, Home, Scale, Settings2, Sun, Moon, Contrast, Waves,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { useT } from '../../i18n'
import { useAppStore } from '../../store/app'
import { useTheme, THEME_LABELS } from '../../theme'
import { OceanLayer } from '../ocean'
import { A11yPanel } from '../a11y/A11yPanel'
import { LiveRegion } from '../../lib/announce'
import { ToastProvider } from '../ui'
import './shell.css'

export function SkipLink() {
  return <a className="lk-skip-link" href="#main">Skip to content</a>
}

const THEME_ICON = { day: Sun, night: Moon, sunlight: Contrast } as const

function ShellHeader({ onOpenA11y }: { onOpenA11y: () => void }) {
  const t = useT()
  const { language, setLanguage, online } = useAppStore()
  const { theme, cycleTheme } = useTheme()
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: api.config })
  const ThemeIcon = THEME_ICON[theme]

  return (
    <header className="topbar">
      <img src="/icon.svg" alt="" aria-hidden="true" />
      <div>
        <h1>{t('app.name')}</h1>
        <span className="tagline">{t('app.tagline')}</span>
      </div>
      <div className="spacer" />
      {config?.date_simulated && (
        <span className="badge sim" role="status">{t('common.simulatedDate')} {config.current_date}</span>
      )}
      {!online && <span className="badge offline" role="status">{t('common.offline').split(' — ')[0]}</span>}
      <div className="lk-shell-actions">
        <button type="button" className="lk-header-btn" onClick={cycleTheme}
          aria-label={`Theme: ${THEME_LABELS[theme]}. Change theme.`}>
          <ThemeIcon size={20} aria-hidden="true" />
        </button>
        <button type="button" className="lk-header-btn" onClick={onOpenA11y}
          aria-label="Display and accessibility settings">
          <Settings2 size={20} aria-hidden="true" />
        </button>
        <button
          className="lang-switch"
          onClick={() => setLanguage(language === 'en' ? 'mfe' : 'en')}
          aria-label={t('common.language')}
        >
          {language === 'en' ? 'MFE' : 'EN'}
        </button>
      </div>
    </header>
  )
}

/**
 * Fisher routes only. Authority/verify use PlainShell.
 * @param narrow  caps the content column at 720px for form-heavy pages
 *                (Record a catch, Demo, Queue, Privacy, About) instead of the
 *                960px dashboard width.
 *   wide       — data-dense pages that need the whole viewport rather than the
 *                960px reading column. Sea conditions is seven metric tiles plus
 *                a compass; at 960px they wrap into a ragged 2-up grid with an
 *                orphan tile and a large dead area to its right.
 *                `narrow` wins if both are passed.
 */
export function FisherShell({ narrow, wide, children }:
  { narrow?: boolean; wide?: boolean; children: ReactNode }) {
  const t = useT()
  const [a11yOpen, setA11yOpen] = useState(false)

  // The five primary fisher tasks. These appear in BOTH the desktop side nav
  // and the phone tab bar.
  const navItems = [
    { to: '/', end: true, icon: Home, label: t('nav.dashboard') },
    { to: '/sea', end: false, icon: Waves, label: t('nav.marine') },
    { to: '/record', end: false, icon: Camera, label: t('nav.catch') },
    { to: '/log', end: false, icon: BookOpen, label: t('nav.history') },
    { to: '/declaration', end: false, icon: Anchor, label: t('nav.declaration') },
  ]

  /**
   * Side nav ONLY — deliberately not in the phone tab bar.
   *
   * /assistant (Lane B's offline rules browser) and /pillars (Lane A's blue-
   * economy surface) shipped as routes in App.tsx with nothing linking to
   * them, so both were reachable only by typing a URL. The nav lives in this
   * file, which is Sahil's lane, so their owners could not have added these
   * without crossing a lane boundary — hence the gap.
   *
   * They go here rather than into navItems because seven targets in a phone
   * tab bar breaks the 56px touch floor at 360px width. Dashboard's tool grid
   * carries them on small screens instead. How the IA should really absorb
   * seven surfaces is a redesign decision, not one to guess at here.
   *
   * Labels reuse the owners' existing page-title keys rather than adding
   * nav.* keys, so this touches no shared i18n file.
   */
  const secondaryNavItems = [
    { to: '/assistant', end: false, icon: Scale, label: t('assistant.title') },
    { to: '/pillars', end: false, icon: Compass, label: t('pillars.title') },
  ]

  return (
    <ToastProvider>
      <SkipLink />
      <OceanLayer />
      <LiveRegion />
      <div className="app-shell lk-content">
        <ShellHeader onOpenA11y={() => setA11yOpen(true)} />

        <div className="app-body">
          <nav className="side-nav" aria-label="Main">
            {[...navItems, ...secondaryNavItems].map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}
                className={({ isActive }) => (isActive ? 'active' : '')}>
                <item.icon size={20} aria-hidden="true" /><span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <main id="main" className={narrow ? 'narrow' : wide ? 'wide' : undefined}>{children}</main>
        </div>

        <nav className="bottom-nav" aria-label="Main">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} aria-label={item.label}
              className={({ isActive }) => (isActive ? 'active' : '')}>
              <item.icon size={22} aria-hidden="true" /><span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <A11yPanel open={a11yOpen} onClose={() => setA11yOpen(false)} />
    </ToastProvider>
  )
}

/**
 * Quiet shell for the shore side (/authority, /verify/:id).
 * No fisher tab bar, no ambient animation — these are working tools and public
 * proof pages, not the on-boat experience.
 *
 * @param chrome  optional top bar; Shirish supplies components/authority's own.
 */
export function PlainShell({ chrome, children }: { chrome?: ReactNode; children: ReactNode }) {
  return (
    <ToastProvider>
      <SkipLink />
      <LiveRegion />
      <div className="app-shell lk-scope">
        {chrome}
        <main id="main" className="lk-plain-main">{children}</main>
      </div>
    </ToastProvider>
  )
}
