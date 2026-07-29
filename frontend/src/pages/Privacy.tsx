import { useT } from '../i18n'

export default function Privacy() {
  const t = useT()
  return (
    <div className="card">
      <h2>{t('privacy.title')}</h2>
      <p>{t('privacy.p1')}</p>
      <p>{t('privacy.p2')}</p>
      <p>{t('privacy.p3')}</p>
      <p className="banner info">{t('limitation.permanent')}</p>
    </div>
  )
}
