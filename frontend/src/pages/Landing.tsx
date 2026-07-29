/**
 * Onboarding — the first screen anyone sees, including judges on a projector.
 *
 * The card is a plotted fix on a living nautical chart of the sea the fisher is
 * about to go out on. The chart is drawn procedurally on a canvas
 * (components/onboarding) — no assets, no requests, works in airplane mode.
 *
 * PRESERVED EXACTLY from the previous version:
 *   - the zustand calls and their order: setLanguage on selection,
 *     setProfile(name, area) then setOnboarded(true) on Koumanse
 *   - local name/area state
 *   - every Morisyen and English string, via the same i18n keys
 *   - the AI-assistance disclaimer (restyled, meaning untouched)
 * The only behavioural change is that Koumanse plays a ~340ms departure before
 * setOnboarded fires, and skips it entirely under reduced motion.
 */
import { useEffect, useRef, useState } from 'react'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'
import { useTheme } from '../theme'
import { useAnnounce } from '../lib/announce'
import { BathymetricScene } from '../components/onboarding/BathymetricScene'
import '../components/onboarding/onboarding.css'

/** Mauritius. Set small in mono along the card's lower edge. */
const FIX = '20°10′S  57°30′E'

const DEPART_MS = 340

/**
 * Real Mauritian landing sites, offered as a native <datalist>. This SUGGESTS
 * and never restricts: the input stays free text, so a fisher working from a
 * spot that is not on the list is not blocked by it.
 */
const LANDING_SITES = [
  'Grand Baie', 'Grand Gaube', 'Trou aux Biches', 'Port Louis', 'Albion',
  'Le Morne', 'Souillac', 'Mahébourg', "Trou d'Eau Douce", 'Poste Lafayette',
  'Cap Malheureux', 'Bain Boeuf', 'Tamarin', 'Black River', "Poudre d'Or",
]

export default function Landing() {
  const t = useT()
  const { language, setLanguage, setProfile, setOnboarded } = useAppStore()
  const [name, setName] = useState('')
  const [area, setArea] = useState('')
  const [departing, setDeparting] = useState(false)
  const { reduceMotion } = useTheme()
  const announce = useAnnounce()
  const timer = useRef<number | null>(null)
  const panelRef = useRef<HTMLElement | null>(null)

  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current) }, [])

  const choose = (lang: 'mfe' | 'en') => setLanguage(lang)

  // Counter-parallax: the panel drifts a few px AGAINST the camera orbit, so it
  // reads as nearer to the viewer than the seafloor behind it.
  useEffect(() => {
    if (reduceMotion) return
    const el = panelRef.current
    if (!el) return
    const onMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth) * 2 - 1
      const ny = (e.clientY / window.innerHeight) * 2 - 1
      el.style.setProperty('--panel-dx', `${(-nx * 6).toFixed(1)}px`)
      el.style.setProperty('--panel-dy', `${(-ny * 4).toFixed(1)}px`)
    }
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [reduceMotion])

  const start = () => {
    // Identical store writes to the previous implementation, in the same order.
    const commit = () => { setProfile(name, area); setOnboarded(true) }
    announce(t('landing.start'))
    if (reduceMotion) { commit(); return }
    setDeparting(true)
    timer.current = window.setTimeout(commit, DEPART_MS)
  }

  return (
    <div className={`lk-onboard lk-scope${departing ? ' lk-onboard--departing' : ''}`}>
      <BathymetricScene />

      <div className="lk-onboard__inner">
        <div>
          <div className="lk-onboard__masthead">
            <img src="/icon.svg" alt="" aria-hidden="true" />
            <div>
              <h1 className="lk-onboard__wordmark">{t('app.name')}</h1>
              <span className="lk-onboard__tagline">{t('app.tagline')}</span>
            </div>
          </div>

          <section className="lk-fix" ref={panelRef}>
            <span className="lk-fix__ticks" aria-hidden="true" />

            <h2 className="lk-fix__welcome">{t('landing.welcome')}</h2>
            <p className="lk-fix__intro">{t('landing.intro')}</p>

            <fieldset className="lk-lang">
              <legend className="lk-lang__legend">{t('landing.chooseLanguage')}</legend>
              <div className="lk-lang__options">
                {/* Each input lives in its own cell so it positions against that
                    cell, not against the card. See onboarding.css. */}
                <div className="lk-lang__cell">
                  <input className="lk-lang__input" type="radio" id="lk-lang-mfe" name="lk-language"
                    checked={language === 'mfe'} onChange={() => choose('mfe')} />
                  <label className="lk-lang__option" htmlFor="lk-lang-mfe">
                    <span className="lk-lang__marker" aria-hidden="true" />
                    Kreol Morisien
                  </label>
                </div>

                <div className="lk-lang__cell">
                  <input className="lk-lang__input" type="radio" id="lk-lang-en" name="lk-language"
                    checked={language === 'en'} onChange={() => choose('en')} />
                  <label className="lk-lang__option" htmlFor="lk-lang-en">
                    <span className="lk-lang__marker" aria-hidden="true" />
                    English
                  </label>
                </div>
              </div>
            </fieldset>

            <hr className="lk-fix__divider" />

            <div className="lk-field-stack">
              <div>
                <label className="lk-onboard-label" htmlFor="lk-name">{t('landing.profileName')}</label>
                <input className="lk-onboard-input" id="lk-name" value={name}
                  onChange={(e) => setName(e.target.value)} autoComplete="name" />
              </div>
              <div>
                <label className="lk-onboard-label" htmlFor="lk-area">{t('landing.area')}</label>
                <input className="lk-onboard-input" id="lk-area" value={area}
                  list="lk-landing-sites" autoComplete="off"
                  onChange={(e) => setArea(e.target.value)} placeholder="Grand Baie, Mahébourg…" />
                <datalist id="lk-landing-sites">
                  {LANDING_SITES.map((sIte) => <option key={sIte} value={sIte} />)}
                </datalist>
              </div>
            </div>

            <button className="lk-start" type="button" onClick={start}>
              {t('landing.start')}
            </button>

            <span className="lk-fix__coords" aria-hidden="true">{FIX}</span>
          </section>
        </div>

        <p className="lk-onboard__legend">{t('limitation.permanent')}</p>
      </div>
    </div>
  )
}
