import { useT } from '../i18n'

export default function About() {
  const t = useT()
  return (
    <div className="card">
      <h2>{t('about.title')}</h2>
      <p>{t('about.p1')}</p>
      <p>{t('about.p2')}</p>
      <p className="small">{t('about.team')}</p>
      <p className="banner info">{t('limitation.permanent')}</p>
    </div>
  )
}
