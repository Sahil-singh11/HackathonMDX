/* Workstream 2 — "how to complete a declaration" walkthrough.
 *
 * A static reference, not a wizard: it never claims progress and never touches
 * the real declaration flow (Shirish's lane). Each step links the reader to the
 * page where that step actually happens. The MOCK warning is repeated here
 * because the walkthrough describes a demo submission, not a government filing.
 */
import { Anchor, BookOpen, Camera, FileCheck2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card } from '../components/ui'
import { useT } from '../i18n'

export default function DeclarationGuide() {
  const t = useT()

  const steps = [
    { icon: Camera, titleKey: 'assistant.guide.step1', bodyKey: 'assistant.guide.step1Body', to: '/record' },
    { icon: BookOpen, titleKey: 'assistant.guide.step2', bodyKey: 'assistant.guide.step2Body', to: '/log' },
    { icon: Anchor, titleKey: 'assistant.guide.step3', bodyKey: 'assistant.guide.step3Body', to: '/declaration' },
    { icon: FileCheck2, titleKey: 'assistant.guide.step4', bodyKey: 'assistant.guide.step4Body', to: '/declaration' },
  ]

  return (
    <Card title={t('assistant.guide.title')}>
      <p className="asst-mock-warning" role="note">{t('assistant.guide.mockNote')}</p>
      <ol className="asst-guide">
        {steps.map(({ icon: Icon, titleKey, bodyKey, to }, i) => (
          <li key={titleKey} className="asst-guide__step">
            <span className="asst-guide__num asst-data" aria-hidden="true">{i + 1}</span>
            <div className="asst-guide__body">
              <h3 className="asst-guide__title">
                <Icon size={18} aria-hidden="true" /> {t(titleKey)}
              </h3>
              <p>{t(bodyKey)}</p>
              <Link to={to} className="asst-guide__link">{t('assistant.guide.goThere')}</Link>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  )
}
