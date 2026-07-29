import { useState } from 'react'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'

export default function Landing() {
  const t = useT()
  const { language, setLanguage, setProfile, setOnboarded } = useAppStore()
  const [name, setName] = useState('')
  const [area, setArea] = useState('')

  return (
    <div className="app-shell">
      <header className="topbar">
        <img src="/icon.svg" alt="" aria-hidden="true" />
        <div>
          <h1>{t('app.name')}</h1>
          <span className="tagline">{t('app.tagline')}</span>
        </div>
      </header>
      <main>
        <div className="card">
          <h2>{t('landing.welcome')}</h2>
          <p>{t('landing.intro')}</p>
          <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
            <legend className="small" style={{ fontWeight: 700 }}>{t('landing.chooseLanguage')}</legend>
            <div style={{ display: 'flex', gap: '0.6rem', margin: '0.5rem 0' }}>
              <button className="secondary" aria-pressed={language === 'mfe'}
                style={language === 'mfe' ? { borderColor: 'var(--coral)', background: '#fff4f2' } : undefined}
                onClick={() => setLanguage('mfe')}>Kreol Morisien</button>
              <button className="secondary" aria-pressed={language === 'en'}
                style={language === 'en' ? { borderColor: 'var(--coral)', background: '#fff4f2' } : undefined}
                onClick={() => setLanguage('en')}>English</button>
            </div>
          </fieldset>
          <label className="field">{t('landing.profileName')}
            <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
          </label>
          <label className="field">{t('landing.area')}
            <input value={area} onChange={(e) => setArea(e.target.value)} placeholder="Grand Baie, Mahébourg…" />
          </label>
          <button className="primary" onClick={() => { setProfile(name, area); setOnboarded(true) }}>
            {t('landing.start')}
          </button>
        </div>
        <p className="banner info">{t('limitation.permanent')}</p>
      </main>
    </div>
  )
}
