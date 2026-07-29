import { useQuery } from '@tanstack/react-query'
import { Anchor, BookOpen, Camera, Home, Waves } from 'lucide-react'
import { useEffect } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
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

      <main>
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
      </main>

      <nav className="bottom-nav" aria-label="Main">
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
          <Home size={22} aria-hidden="true" /><span>{t('nav.dashboard')}</span>
        </NavLink>
        <NavLink to="/marine" className={({ isActive }) => (isActive ? 'active' : '')}>
          <Waves size={22} aria-hidden="true" /><span>{t('nav.marine')}</span>
        </NavLink>
        <NavLink to="/catch" className={({ isActive }) => (isActive ? 'active' : '')}>
          <Camera size={22} aria-hidden="true" /><span>{t('nav.catch')}</span>
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => (isActive ? 'active' : '')}>
          <BookOpen size={22} aria-hidden="true" /><span>{t('nav.history')}</span>
        </NavLink>
        <NavLink to="/declaration" className={({ isActive }) => (isActive ? 'active' : '')}>
          <Anchor size={22} aria-hidden="true" /><span>{t('nav.declaration')}</span>
        </NavLink>
      </nav>
    </div>
  )
}
