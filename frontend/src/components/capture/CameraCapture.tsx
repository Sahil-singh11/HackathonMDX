/* In-page camera (Lane B).
 *
 * WHY THIS EXISTS. "Take a photo" used to be an <input capture="environment">.
 * That attribute is honoured only by MOBILE browsers; desktop Chrome, Edge and
 * Firefox ignore it completely and open the ordinary file picker. So on a laptop
 * the button labelled "Take a photo" opened a file explorer — the label promised
 * something the markup could not deliver.
 *
 * getUserMedia works on desktop, so this opens a real viewfinder, grabs a frame
 * and hands back a File exactly as the file input did. Everything downstream —
 * the blur/brightness pre-check, the preview, the analyse call — is unchanged,
 * because the output is still just a File.
 *
 * The stream is stopped on every exit path (shutter, cancel, Escape, unmount).
 * A forgotten track leaves the camera light on, which on someone's laptop reads
 * as the app spying on them.
 *
 * Props:
 *   onCapture  (f: File) => void   frame grabbed
 *   onCancel   () => void
 *   onUnavailable () => void       no camera / permission denied — caller falls
 *                                  back to the file picker
 */
import { Camera, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useT } from '../../i18n'

interface Props {
  onCapture: (file: File) => void
  onCancel: () => void
  onUnavailable: (reason: 'denied' | 'none' | 'error') => void
}

export default function CameraCapture({ onCapture, onCancel, onUnavailable }: Props) {
  const t = useT()
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const closeRef = useRef<HTMLButtonElement | null>(null)
  const [ready, setReady] = useState(false)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          // `ideal`, not `exact`: a laptop has no environment-facing camera and
          // `exact` would reject outright rather than fall back to the webcam.
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 } },
          audio: false,
        })
        if (cancelled) { stream.getTracks().forEach((tr) => tr.stop()); return }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play().catch(() => {})
        }
        setReady(true)
        closeRef.current?.focus()
      } catch (err) {
        if (cancelled) return
        const name = (err as DOMException)?.name
        onUnavailable(
          name === 'NotAllowedError' || name === 'SecurityError' ? 'denied'
            : name === 'NotFoundError' || name === 'OverconstrainedError' ? 'none'
              : 'error',
        )
      }
    })()

    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel() }
    document.addEventListener('keydown', onKey)

    return () => {
      cancelled = true
      document.removeEventListener('keydown', onKey)
      stop()
    }
  }, [onCancel, onUnavailable, stop])

  const shoot = () => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob((blob) => {
      if (!blob) return
      stop()
      onCapture(new File([blob], `catch-${Date.now()}.jpg`, { type: 'image/jpeg' }))
    }, 'image/jpeg', 0.92)
  }

  return (
    <div className="cam-backdrop" role="dialog" aria-modal="true" aria-label={t('catch.cameraTitle')}>
      <div className="cam-panel">
        <div className="cam-head">
          <span className="cam-title">{t('catch.cameraTitle')}</span>
          <button ref={closeRef} type="button" className="cam-close"
            onClick={onCancel} aria-label={t('catch.cameraCancel')}>
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <div className="cam-stage">
          {/* muted + playsInline are both required for autoplay on iOS. */}
          <video ref={videoRef} className="cam-video" muted playsInline
            aria-label={t('catch.cameraLive')} />
          {!ready && <p className="cam-starting">{t('catch.cameraStarting')}</p>}
        </div>

        <div className="cam-actions">
          <button type="button" className="primary cam-shoot" onClick={shoot} disabled={!ready}>
            <Camera size={20} aria-hidden="true" /> {t('catch.cameraShoot')}
          </button>
          <button type="button" className="secondary cam-cancel" onClick={onCancel}>
            {t('catch.cameraCancel')}
          </button>
        </div>
      </div>
    </div>
  )
}
