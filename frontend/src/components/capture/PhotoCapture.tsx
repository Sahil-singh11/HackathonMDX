/* Photo capture zone (Lane B).
 *
 * Props:
 *   preview      string | null   object URL of the chosen photo
 *   busy         boolean         analysis in flight (shows shimmer, locks retake)
 *   preCheck     PreCheckResult | null   client-side verdict for the current photo
 *   onFile       (f: File|null) => void  chosen file, or null when cleared
 */
import { Camera, Images, RotateCcw } from 'lucide-react'
import { useRef } from 'react'
import { useT } from '../../i18n'
import type { PreCheckResult } from './imageQuality'

interface Props {
  preview: string | null
  busy: boolean
  preCheck: PreCheckResult | null
  onFile: (f: File | null) => void
}

export default function PhotoCapture({ preview, busy, preCheck, onFile }: Props) {
  const t = useT()
  const cameraInput = useRef<HTMLInputElement>(null)
  const galleryInput = useRef<HTMLInputElement>(null)

  const pick = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFile(e.target.files?.[0] ?? null)
    e.target.value = '' // allow re-picking the same file after a retake
  }

  return (
    <div className="capture-zone-wrap">
      <div className={`catch-photo-zone${preview ? ' has-image' : ''}`}>
        {preview ? (
          <>
            <img src={preview} alt={t('catch.previewAlt')} className="photo-fill" />
            {busy && <div className="photo-shimmer" aria-hidden="true" />}
            <button type="button" className="photo-retake-btn" disabled={busy}
              aria-label={t('catch.retake')}
              onClick={() => onFile(null)}>
              <RotateCcw size={20} aria-hidden="true" />
            </button>
          </>
        ) : (
          <div className="catch-photo-empty">
            <Camera size={48} className="photo-icon" aria-hidden="true" />
            <h2>{t('catch.takePhoto')}</h2>

            {/* Shot guidance the fisher acts on — each line says why it matters. */}
            {/* 2x2 grid rather than four stacked full-width sentences: the
                guidance is the same, but it stops the upload zone from being
                taller than the rest of the form put together. */}
            <ul className="photo-guidance">
              <li><strong>{t('catch.tip.goodLight')}</strong><span>{t('catch.tip.goodLightWhy')}</span></li>
              <li><strong>{t('catch.tip.wholeFish')}</strong><span>{t('catch.tip.wholeFishWhy')}</span></li>
              <li><strong>{t('catch.tip.addRuler')}</strong><span>{t('catch.tip.addRulerWhy')}</span></li>
              <li><strong>{t('catch.tip.avoidFaces')}</strong><span>{t('catch.tip.avoidFacesWhy')}</span></li>
            </ul>

            <div className="capture-actions">
              <button type="button" className="primary capture-btn"
                onClick={() => cameraInput.current?.click()}>
                <Camera size={20} aria-hidden="true" /> {t('catch.useCamera')}
              </button>
              <button type="button" className="secondary capture-btn"
                onClick={() => galleryInput.current?.click()}>
                <Images size={20} aria-hidden="true" /> {t('catch.useGallery')}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Two inputs: capture="environment" opens the rear camera on mobile, the
          second is the gallery fallback (and the only one that works on desktop). */}
      <input ref={cameraInput} type="file" accept="image/*" capture="environment"
        className="sr-only" aria-label={t('catch.useCamera')} onChange={pick} />
      <input ref={galleryInput} type="file" accept="image/*"
        className="sr-only" aria-label={t('catch.useGallery')} onChange={pick} />

      {preCheck && preCheck.verdict !== 'ok' && (
        <div className="banner warn precheck-warning" role="status">
          <strong>{t(`catch.precheck.${preCheck.verdict}`)}</strong>
          <span>{t('catch.precheck.advice')}</span>
          <button type="button" className="secondary precheck-retake"
            onClick={() => onFile(null)}>{t('catch.retake')}</button>
        </div>
      )}
    </div>
  )
}
