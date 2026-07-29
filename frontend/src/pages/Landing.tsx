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
import { useQuery } from '@tanstack/react-query'
import { Check, MapPin, Thermometer, Timer, User, Waves } from 'lucide-react'
import { api } from '../api/client'
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

/**
 * The tagline is one sentence pair ("X. Y.") in both languages. Split on the
 * first sentence boundary so it reads as two lines — the copy itself is
 * untouched, only where it wraps.
 */
function taglineLines(s: string): [string, string] {
  const i = s.indexOf('. ')
  if (i < 0) return [s, '']
  return [s.slice(0, i + 1), s.slice(i + 2)]
}

function formatClock(ms: number): string {
  const d = new Date(ms)
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

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

  const { data: marine, dataUpdatedAt } = useQuery({ queryKey: ['marine'], queryFn: api.marine, retry: false })
  const waveHeight = typeof marine?.wave_height_m === 'number' ? marine.wave_height_m as number : null
  const swellPeriod = typeof marine?.swell_period_s === 'number' ? marine.swell_period_s as number : null
  const seaTemp = typeof marine?.sea_surface_temperature_c === 'number' ? marine.sea_surface_temperature_c as number : null
  const conditionsAt = dataUpdatedAt ? formatClock(dataUpdatedAt) : null

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

  const go = (finalName: string, finalArea: string) => {
    // Identical store writes to the previous implementation, in the same order.
    const commit = () => { setProfile(finalName, finalArea); setOnboarded(true) }
    announce(t('landing.start'))
    if (reduceMotion) { commit(); return }
    setDeparting(true)
    timer.current = window.setTimeout(commit, DEPART_MS)
  }

  const start = () => go(name, area)
  // Both fields are already optional — this just skips whatever is half-typed
  // and commits with defaults, rather than requiring the fields to be cleared.
  const startAsGuest = () => go('', '')

  const [wLabel, wUnit] = waveHeight != null ? [waveHeight.toFixed(1), 'm'] : [null, null]
  const [pLabel, pUnit] = swellPeriod != null ? [swellPeriod.toFixed(0), 's'] : [null, null]
  const [sLabel, sUnit] = seaTemp != null ? [seaTemp.toFixed(1), '°C'] : [null, null]
  const [taglineA, taglineB] = taglineLines(t('app.tagline'))

  return (
    <div className={`lk-onboard lk-scope${departing ? ' lk-onboard--departing' : ''}`}>
      <BathymetricScene />

      <div className="lk-onboard__inner">
        <div className="lk-onboard__left">
          <div className="lk-onboard__masthead">
            <img src="/icon.svg" alt="" aria-hidden="true" />
            <div>
              <h1 className="lk-onboard__wordmark">{t('app.name')}</h1>
              <span className="lk-onboard__tagline">
                {taglineA}
                {taglineB && <><br />{taglineB}</>}
              </span>
            </div>
          </div>

          <section className="lk-fix" ref={panelRef}>
            <span className="lk-fix__ticks" aria-hidden="true" />

            <h2 className="lk-fix__welcome">{t('landing.welcome')}</h2>
            <p className="lk-fix__intro">{t('landing.intro')}</p>

            <fieldset className="lk-lang">
              <legend className="lk-lang__legend">{t('landing.chooseLanguage')}</legend>
              <div className="lk-lang__pill">
                <div className="lk-lang__cell">
                  <input className="lk-lang__input" type="radio" id="lk-lang-mfe" name="lk-language"
                    checked={language === 'mfe'} onChange={() => choose('mfe')} />
                  <label className="lk-lang__option" htmlFor="lk-lang-mfe">
                    <Check className="lk-lang__check" size={18} aria-hidden="true" />
                    Kreol Morisien
                  </label>
                </div>

                <div className="lk-lang__cell">
                  <input className="lk-lang__input" type="radio" id="lk-lang-en" name="lk-language"
                    checked={language === 'en'} onChange={() => choose('en')} />
                  <label className="lk-lang__option" htmlFor="lk-lang-en">
                    <Check className="lk-lang__check" size={18} aria-hidden="true" />
                    English
                  </label>
                </div>
              </div>
            </fieldset>

            <hr className="lk-fix__divider" />

            <div className="lk-field-stack">
              <div>
                <label className="lk-onboard-label" htmlFor="lk-name">{t('landing.profileName')}</label>
                <div className="lk-onboard-field">
                  <User className="lk-onboard-field__icon" size={18} aria-hidden="true" />
                  <input className="lk-onboard-input" id="lk-name" value={name}
                    onChange={(e) => setName(e.target.value)} autoComplete="name" />
                </div>
              </div>
              <div>
                <label className="lk-onboard-label" htmlFor="lk-area">{t('landing.area')}</label>
                <div className="lk-onboard-field">
                  <MapPin className="lk-onboard-field__icon" size={18} aria-hidden="true" />
                  <input className="lk-onboard-input" id="lk-area" value={area}
                    list="lk-landing-sites" autoComplete="off"
                    onChange={(e) => setArea(e.target.value)} placeholder="Grand Baie, Mahébourg…" />
                  <datalist id="lk-landing-sites">
                    {LANDING_SITES.map((sIte) => <option key={sIte} value={sIte} />)}
                  </datalist>
                </div>
              </div>
            </div>

            <button className="lk-start" type="button" onClick={start}>
              {t('landing.start')}
            </button>
            <button className="lk-start-guest" type="button" onClick={startAsGuest}>
              {t('landing.guest')}
            </button>

            <span className="lk-fix__coords" aria-hidden="true">{FIX}</span>
          </section>

          <p className="lk-onboard__legend">{t('limitation.permanent')}</p>

          <p className="lk-onboard__footer">
            {t('landing.footerSupport')} · {t('landing.footerLocale')}
          </p>
        </div>

        <div className="lk-onboard__scene-space" aria-hidden="true" />

        <div className="lk-conditions" role="group" aria-label={t('landing.conditions')}>
          <span className="lk-conditions__title">{t('landing.conditions')}</span>
          <div className="lk-conditions__row">
            <div className="lk-conditions__item">
              <Waves className="lk-conditions__icon" size={20} aria-hidden="true" />
              <div>
                <span className="lk-conditions__value">
                  {wLabel ?? '—'}{wUnit && <span className="lk-conditions__unit">{wUnit}</span>}
                </span>
                <span className="lk-conditions__label">
                  {t('marine.waveHeight')}{wLabel == null && ` · ${t('landing.noDataYet')}`}
                </span>
              </div>
            </div>
            <div className="lk-conditions__item">
              <Timer className="lk-conditions__icon" size={20} aria-hidden="true" />
              <div>
                <span className="lk-conditions__value">
                  {pLabel ?? '—'}{pUnit && <span className="lk-conditions__unit">{pUnit}</span>}
                </span>
                <span className="lk-conditions__label">
                  {t('marine.swellPeriod')}{pLabel == null && ` · ${t('landing.noDataYet')}`}
                </span>
              </div>
            </div>
            <div className="lk-conditions__item">
              <Thermometer className="lk-conditions__icon" size={20} aria-hidden="true" />
              <div>
                <span className="lk-conditions__value">
                  {sLabel ?? '—'}{sUnit && <span className="lk-conditions__unit">{sUnit}</span>}
                </span>
                <span className="lk-conditions__label">
                  {t('marine.sst')}{sLabel == null && ` · ${t('landing.noDataYet')}`}
                </span>
              </div>
            </div>
          </div>
          {conditionsAt && <span className="lk-conditions__updated">{t('marine.updated')} {conditionsAt}</span>}
        </div>
      </div>
    </div>
  )
}
