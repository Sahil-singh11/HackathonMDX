/* Staged analysis progress (Lane B).
 *
 * The backend answers /api/analyse-catch as one opaque request with no phase
 * events, so these stages are a perceived-progress indicator, not server
 * telemetry. The label says "this can take a moment" rather than implying a
 * measured percentage — we do not invent precision we do not have.
 *
 * Cancelling is always available: on a boat, waiting is a choice.
 *
 * Props:
 *   stage     number             0-based index of the active stage
 *   onCancel  () => void
 */
import { Check, X } from 'lucide-react'
import { useT } from '../../i18n'

interface Props {
  stage: number
  onCancel: () => void
}

export default function AnalyseProgress({ stage, onCancel }: Props) {
  const t = useT()
  const stages = [
    { key: 'scan', label: t('catch.progress.scan') },
    { key: 'match', label: t('catch.progress.match') },
    { key: 'rules', label: t('catch.progress.rules') },
  ]

  return (
    <div className="analyse-progress">
      <div className="progress-tracker">
        {stages.map((s, i) => (
          <div key={s.key}
            className={`progress-step${i === stage ? ' active' : i < stage ? ' done' : ''}`}>
            {i < stage ? <Check size={14} aria-hidden="true" /> : <span className="dot" />}
            {s.label}
          </div>
        ))}
      </div>
      <p className="small progress-note">{t('catch.progress.patience')}</p>
      <button type="button" className="secondary cancel-analyse" onClick={onCancel}>
        <X size={16} aria-hidden="true" /> {t('catch.cancelAnalysis')}
      </button>
    </div>
  )
}
