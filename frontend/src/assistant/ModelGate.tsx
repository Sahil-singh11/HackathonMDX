/* Workstream 2 — model download consent + progress gate.
 *
 * A 2 GB download is a serious ask for a fisher on mobile data, so it is never
 * started implicitly. This component:
 *   - feature-detects WebGPU/OPFS and refuses cleanly when unsupported
 *   - states the REAL artifact size before asking (~2.0 GB, not the 1.3 GB in
 *     the brief — see modelCache.ts)
 *   - warns when the browser reports insufficient storage headroom
 *   - shows real byte progress, and lets the download be cancelled
 *   - treats declining as a normal outcome that returns to the rules browser
 *
 * Props:
 *   onReady   (model: File) => void   cached model is available
 *   onDecline () => void              user chose the rules browser instead
 */
import { AlertTriangle, Download, HardDrive, Trash2, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Badge, Button, Card } from '../components/ui'
import { useT } from '../i18n'
import { useAnnounce } from '../lib/announce'
import { detectCapabilityCached } from './engine'
import {
  MODEL_BYTES_DOCUMENTED, deleteCachedModel, downloadModel, estimateStorage,
  formatBytes, getCachedModel, requestPersistence,
  type DownloadProgress, type StorageEstimate,
} from './modelCache'

type Phase = 'checking' | 'unsupported' | 'offer' | 'downloading' | 'ready' | 'error'

interface Props {
  onReady: (model: File) => void
  onDecline: () => void
}

export default function ModelGate({ onReady, onDecline }: Props) {
  const t = useT()
  const announce = useAnnounce()
  const [phase, setPhase] = useState<Phase>('checking')
  const [reason, setReason] = useState<string>('')
  const [progress, setProgress] = useState<DownloadProgress | null>(null)
  const [storage, setStorage] = useState<StorageEstimate | null>(null)
  const [controller, setController] = useState<AbortController | null>(null)
  const [errorText, setErrorText] = useState('')

  useEffect(() => {
    let cancelled = false
    void (async () => {
      const cap = await detectCapabilityCached()
      if (cancelled) return
      if (!cap.supported) {
        setReason(cap.reason)
        setPhase('unsupported')
        return
      }
      const cached = await getCachedModel()
      if (cancelled) return
      if (cached) { setPhase('ready'); onReady(cached); return }
      setStorage(await estimateStorage())
      if (!cancelled) setPhase('offer')
    })()
    return () => { cancelled = true }
  }, [onReady])

  const start = useCallback(async () => {
    const ac = new AbortController()
    setController(ac)
    setPhase('downloading')
    setProgress({ receivedBytes: 0, totalBytes: null })
    await requestPersistence()
    try {
      const file = await downloadModel(setProgress, ac.signal)
      setPhase('ready')
      announce(t('assistant.model.a11yReady'))
      onReady(file)
    } catch (err) {
      if (ac.signal.aborted) {
        setPhase('offer')
        announce(t('assistant.model.a11yCancelled'))
        return
      }
      setErrorText(err instanceof Error ? err.message : String(err))
      setPhase('error')
    } finally {
      setController(null)
    }
  }, [announce, onReady, t])

  if (phase === 'checking') {
    return <Card><p>{t('assistant.model.checking')}</p></Card>
  }

  if (phase === 'unsupported') {
    return (
      <Card title={t('assistant.model.unsupportedTitle')}>
        <p>{t(reason === 'no-webgpu' ? 'assistant.model.noWebgpu' : 'assistant.model.noOpfs')}</p>
        <p className="asst-intro">{t('assistant.model.unsupportedFallback')}</p>
        <Button variant="primary" onClick={onDecline}>{t('assistant.model.useRules')}</Button>
      </Card>
    )
  }

  if (phase === 'downloading') {
    const pct = progress?.totalBytes
      ? Math.round((progress.receivedBytes / progress.totalBytes) * 100)
      : null
    return (
      <Card title={t('assistant.model.downloadingTitle')}>
        <progress
          className="asst-progress"
          value={pct ?? undefined}
          max={pct != null ? 100 : undefined}
          aria-label={t('assistant.model.downloadingTitle')}
        />
        <p className="asst-data">
          {formatBytes(progress?.receivedBytes ?? 0)}
          {progress?.totalBytes ? ` / ${formatBytes(progress.totalBytes)}` : ''}
          {pct != null ? ` · ${pct}%` : ''}
        </p>
        <p className="asst-intro">{t('assistant.model.downloadingNote')}</p>
        <Button variant="secondary" icon={<X size={16} aria-hidden="true" />}
          onClick={() => controller?.abort()}>
          {t('assistant.model.cancel')}
        </Button>
      </Card>
    )
  }

  if (phase === 'error') {
    return (
      <Card title={t('assistant.model.errorTitle')}>
        <p>{t('assistant.model.errorBody')}</p>
        <p className="asst-data asst-error-detail">{errorText}</p>
        <div className="asst-gate-actions">
          <Button variant="primary" onClick={start}>{t('assistant.model.retry')}</Button>
          <Button variant="secondary" onClick={onDecline}>{t('assistant.model.useRules')}</Button>
        </div>
      </Card>
    )
  }

  if (phase === 'ready') {
    return (
      <Card title={t('assistant.model.readyTitle')}>
        <p>{t('assistant.model.readyBody')}</p>
        <Button variant="secondary" icon={<Trash2 size={16} aria-hidden="true" />}
          onClick={async () => { await deleteCachedModel(); setPhase('offer') }}>
          {t('assistant.model.deleteCache')}
        </Button>
      </Card>
    )
  }

  // phase === 'offer'
  return (
    <Card
      title={t('assistant.model.offerTitle')}
      action={<Badge tone="warning" icon={<HardDrive size={14} aria-hidden="true" />}>
        {formatBytes(MODEL_BYTES_DOCUMENTED)}
      </Badge>}
    >
      <p>{t('assistant.model.offerBody')}</p>

      <ul className="asst-model-facts">
        <li><strong>{formatBytes(MODEL_BYTES_DOCUMENTED)}</strong> — {t('assistant.model.factSize')}</li>
        <li>{t('assistant.model.factOnce')}</li>
        <li>{t('assistant.model.factTextOnly')}</li>
        <li>{t('assistant.model.factPrivate')}</li>
      </ul>

      {storage?.insufficient && (
        <p className="asst-storage-warning">
          <AlertTriangle size={16} aria-hidden="true" />
          {t('assistant.model.lowStorage')}
          {storage.quotaBytes != null && (
            <span className="asst-data"> ({formatBytes(storage.quotaBytes - (storage.usageBytes ?? 0))})</span>
          )}
        </p>
      )}

      <div className="asst-gate-actions">
        <Button variant="primary" icon={<Download size={18} aria-hidden="true" />} onClick={start}>
          {t('assistant.model.download')}
        </Button>
        <Button variant="secondary" onClick={onDecline}>
          {t('assistant.model.decline')}
        </Button>
      </div>
      <p className="asst-intro">{t('assistant.model.declineHint')}</p>
    </Card>
  )
}
