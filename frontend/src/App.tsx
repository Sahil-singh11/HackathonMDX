import { useQuery } from '@tanstack/react-query'
import { Anchor, BookOpen, Camera, Home, Waves } from 'lucide-react'
import { useEffect } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './api/client'
import { useT } from './i18n'
import About from './pages/About'
import CatchFlow from './pages/CatchFlow'
import Dashboard from './pages/Dashboard'
import Declaration from './pages/Declaration'
import DemoControls from './pages/DemoControls'
import History from './pages/History'
import Landing from './pages/Landing'
import Marine from './pages/Marine'
import Privacy from './pages/Privacy'
import Proof from './pages/Proof'
import Queue from './pages/Queue'
import { useAppStore } from './store/app'

export default function App() {
  const t = useT()
  const location = useLocation()
  const { language, setLanguage, onboarded, online, setOnline } = useAppStore()
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: api.config })

  useEffect(() => {
    const up = () => setOnline(true)
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', down) }
  }, [setOnline])

  if (!onboarded) return <Landing />

  const narrowRoutes = ['/catch', '/demo', '/queue', '/privacy', '/about']
  const isNarrow = narrowRoutes.includes(location.pathname)

  const navItems = [
    { to: '/', end: true, icon: Home, label: t('nav.dashboard') },
    { to: '/marine', end: false, icon: Waves, label: t('nav.marine') },
    { to: '/catch', end: false, icon: Camera, label: t('nav.catch') },
    { to: '/history', end: false, icon: BookOpen, label: t('nav.history') },
    { to: '/declaration', end: false, icon: Anchor, label: t('nav.declaration') },
  ]

  return (
    <div className="app-shell">
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
        <button
          className="lang-switch"
          onClick={() => setLanguage(language === 'en' ? 'mfe' : 'en')}
          aria-label={t('common.language')}
        >
          {language === 'en' ? 'MFE' : 'EN'}
        </button>
      </header>

      <div className="app-body">
        <nav className="side-nav" aria-label="Main">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}
              className={({ isActive }) => (isActive ? 'active' : '')}>
              <item.icon size={20} aria-hidden="true" /><span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <main className={isNarrow ? 'narrow' : undefined}>
          <div key={location.pathname} className="page-transition">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/marine" element={<Marine />} />
              <Route path="/catch" element={<CatchFlow />} />
              <Route path="/history" element={<History />} />
              <Route path="/declaration" element={<Declaration />} />
              <Route path="/queue" element={<Queue />} />
              <Route path="/proof" element={<Proof />} />
              <Route path="/demo" element={<DemoControls />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </div>
        </main>
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
  )
}
