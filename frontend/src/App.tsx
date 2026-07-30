/**
 * Router + app root.  FROZEN after Phase 0 — nobody edits this file again.
 *
 * Every route is registered here pointing at its final file location, so the
 * three lanes never have to touch a shared file. If you need a new route, ask
 * Sahil; do not add it yourself.
 *
 * ROUTE MAP
 *   Sahil    /            Home            (pages/Dashboard)
 *            /sea         Sea conditions  (pages/Marine)
 *            /demo        Demo controls
 *            /privacy     Privacy
 *            /about       Impact & about
 *   Dhanesh  /record      Record a catch  (pages/CatchFlow)
 *            /log         Catch log       (pages/History)
 *            /queue       Offline queue
 *            /pillars     Blue-economy pillar index + /pillars/:id detail
 *                         (pillars/) — added by Workstream 2, pillar phase.
 *                         Sahil: second one-line touch of your file, same reason.
 *            /assistant   Rules assistant (assistant/AssistantPage) — added by
 *                         Workstream 2; Sahil, this is the one line that needed
 *                         your file. Route name chosen to avoid Lane C's paths.
 *   Shirish  /declaration Declaration
 *            /authority   Authority dashboard      (stub)
 *            /verify/:id  Certificate verification (stub)
 *            /proof       Technical proof — check against /verify/:id before
 *                         building anything new; the two overlap.
 *
 * Legacy paths (/marine, /catch, /history) redirect to the new IA names so any
 * bookmark, QR code or demo script that already exists keeps working.
 *
 * Fisher routes render inside <FisherShell> (ambient ocean layer + tab bar).
 * /authority and /verify render inside <PlainShell>: no fisher chrome and no
 * ambient animation — they are a working tool and a public proof page.
 */
import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AssistantPage from './assistant/AssistantPage'
import PillarDetail from './pillars/PillarDetail'
import PillarsIndex from './pillars/PillarsIndex'
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
import { AuthorityStub, VerifyStub } from './pages/stubs'
import { FisherShell, PlainShell } from './components/shell'
import { useAppStore } from './store/app'

/**
 * Form-heavy pages read better in a narrower column than dashboards do, so they
 * cap at 720px instead of 960px. Route names changed in Phase 0 — keep this list
 * in sync or those pages silently stretch to full dashboard width.
 */
const NARROW_ROUTES = ['/demo', '/queue', '/privacy', '/about']
/** Data-dense pages that use the full viewport instead of the reading column. */
/* /record moved out of NARROW_ROUTES: the narrow reading column is right for
   prose-ish forms, but the capture step is a TWO-COLUMN form. At 720px each
   column was ~340px, which forced the five context chips onto three 56px rows
   (214px measured) and pushed the step past the viewport. */
const WIDE_ROUTES = ['/sea', '/record']

/** Fisher-side routes, wrapped in the full shell. */
function FisherRoutes() {
  const location = useLocation()
  const isNarrow = NARROW_ROUTES.includes(location.pathname)
  const isWide = WIDE_ROUTES.includes(location.pathname)
  return (
    <FisherShell narrow={isNarrow} wide={isWide}>
      <div key={location.pathname} className="page-transition">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sea" element={<Marine />} />
          <Route path="/record" element={<CatchFlow />} />
          <Route path="/log" element={<History />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/pillars" element={<PillarsIndex />} />
          <Route path="/pillars/:id" element={<PillarDetail />} />
          <Route path="/declaration" element={<Declaration />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/proof" element={<Proof />} />
          <Route path="/demo" element={<DemoControls />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/about" element={<About />} />

          {/* Legacy paths kept alive so existing links do not 404. */}
          <Route path="/marine" element={<Navigate to="/sea" replace />} />
          <Route path="/catch" element={<Navigate to="/record" replace />} />
          <Route path="/history" element={<Navigate to="/log" replace />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </FisherShell>
  )
}

export default function App() {
  const { onboarded, setOnline } = useAppStore()
  const location = useLocation()

  useEffect(() => {
    const up = () => setOnline(true)
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', down) }
  }, [setOnline])

  // The shore-side surfaces are reachable WITHOUT onboarding: an officer or a
  // buyer scanning a QR code is not a fisher, and must never be asked to pick a
  // fishing area before they can see a certificate.
  const isShoreSide = location.pathname.startsWith('/authority')
    || location.pathname.startsWith('/verify')

  if (isShoreSide) {
    return (
      <PlainShell>
        <Routes>
          <Route path="/authority/*" element={<AuthorityStub />} />
          <Route path="/verify/:id" element={<VerifyStub />} />
          <Route path="/verify" element={<VerifyStub />} />
        </Routes>
      </PlainShell>
    )
  }

  if (!onboarded) return <Landing />

  return <FisherRoutes />
}
