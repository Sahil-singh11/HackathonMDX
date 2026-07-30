import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, MapPin, Ruler, ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type AnalyseResponse, type ConfirmResponse, type SpeciesCandidate } from '../api/client'
import '../components/capture/capture.css'
import AssistantBot from '../components/assistantbot/AssistantBot'
import AnalyseProgress from '../components/capture/AnalyseProgress'
import ContextChips from '../components/capture/ContextChips'
import NoteField from '../components/capture/NoteField'
import PhotoCapture from '../components/capture/PhotoCapture'
import ResultPanel from '../components/capture/ResultPanel'
import { preCheckPhoto, type PreCheckResult } from '../components/capture/imageQuality'
import { useAnnounce } from '../components/capture/useAnnounce'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'
import { enqueue } from '../utils/idb'

type Step = 'photo' | 'suggestion' | 'measure' | 'result'

export default function CatchFlow() {
  const t = useT()
  const queryClient = useQueryClient()
  const { announce, LiveRegion } = useAnnounce()
  const { language, fishingArea, online, setLastAnalysis } = useAppStore()

  const [step, setStep] = useState<Step>('photo')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [preCheck, setPreCheck] = useState<PreCheckResult | null>(null)
  const [note, setNote] = useState('')
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [contextTags, setContextTags] = useState<string[]>([])
  const [analysis, setAnalysis] = useState<AnalyseResponse | null>(null)
  const [selectedSpecies, setSelectedSpecies] = useState<string | null>(null)
  const [length, setLength] = useState('')
  const [count, setCount] = useState('1')
  const [area, setArea] = useState(fishingArea)
  const [result, setResult] = useState<ConfirmResponse | null>(null)
  const [queuedId, setQueuedId] = useState<string | null>(null)
  const [progressStage, setProgressStage] = useState(0)
  const [showCheckmark, setShowCheckmark] = useState(false)

  // Set when the fisher cancels: the request cannot be aborted without changing
  // the shared api client, so we discard its result instead of acting on it.
  const cancelledRef = useRef(false)

  const { data: speciesData } = useQuery({ queryKey: ['species'], queryFn: api.species })
  const allSpecies: SpeciesCandidate[] = speciesData?.species ?? []
  const speciesById = new Map(allSpecies.map((s) => [s.species_id, s]))
  const speciesLabel = (id: string) => speciesById.get(id)?.english ?? id

  const analyseMut = useMutation({
    mutationFn: async () => {
      const form = new FormData()
      if (file) form.append('image', file)
      const fullNote = [note, ...contextTags.map((k) => t(k))].filter(Boolean).join(', ')
      if (fullNote) form.append('note', fullNote)
      form.append('language', language)
      return api.analyse(form)
    },
    onSuccess: (data) => {
      if (cancelledRef.current) return
      setAnalysis(data)
      setLastAnalysis(data.provider, data.function_trace)
      if (data.image_quality.status !== 'invalid') {
        setSelectedSpecies(data.species_suggestion.species_id)
        setStep('suggestion')
        announce(t('catch.a11y.analysisReady'))
      } else {
        announce(t('catch.quality.invalid'))
      }
    },
    onError: () => { if (!cancelledRef.current) announce(t('common.error')) },
  })

  const confirmMut = useMutation({
    mutationFn: async () => {
      const body = {
        confirmed_species_id: selectedSpecies,
        measured_length_cm: length ? parseFloat(length) : null,
        count: parseInt(count || '1', 10),
        fishing_area: area,
      }
      if (analysis) return api.confirm(analysis.analysis_id, body)
      return api.createCatch(body)
    },
    onSuccess: (data) => {
      setResult(data)
      setStep('result')
      queryClient.invalidateQueries({ queryKey: ['catches'] })
      announce(t('catch.a11y.saved'))
    },
    onError: () => announce(t('common.error')),
  })

  const onFile = async (f: File | null) => {
    setFile(f)
    setPreCheck(null)
    setPreview((old) => { if (old) URL.revokeObjectURL(old); return f ? URL.createObjectURL(f) : null })
    if (!f) { setAnalysis(null); return }
    const verdict = await preCheckPhoto(f)
    setPreCheck(verdict)
    if (verdict.verdict !== 'ok') announce(t(`catch.precheck.${verdict.verdict}`))
  }

  const cancelAnalysis = () => {
    cancelledRef.current = true
    analyseMut.reset()
    setProgressStage(0)
    announce(t('catch.a11y.cancelled'))
  }

  const startAnalysis = () => {
    cancelledRef.current = false
    analyseMut.mutate()
  }

  const queueOffline = async () => {
    if (!selectedSpecies) return
    const capture_date = new Date().toISOString().slice(0, 10)
    await enqueue({
      species_id: selectedSpecies,
      measured_length_cm: length ? parseFloat(length) : null,
      count: parseInt(count || '1', 10),
      capture_date,
      fishing_area: area,
      queued_at: new Date().toISOString(),
    })
    setQueuedId(`${selectedSpecies}-${capture_date}`)
    announce(t('catch.queued'))
  }

  // Perceived-progress stages; see AnalyseProgress for why these are not real
  // server phase events.
  useEffect(() => {
    if (!analyseMut.isPending) { setProgressStage(0); return }
    const a = setTimeout(() => setProgressStage(1), 1200)
    const b = setTimeout(() => setProgressStage(2), 2600)
    return () => { clearTimeout(a); clearTimeout(b) }
  }, [analyseMut.isPending])

  useEffect(() => {
    if (step !== 'result') return
    setShowCheckmark(true)
    const timer = setTimeout(() => setShowCheckmark(false), 900)
    return () => clearTimeout(timer)
  }, [step])

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  const resetForNext = () => {
    setStep('photo'); setAnalysis(null); setResult(null); onFile(null)
    setNote(''); setLength(''); setCount('1'); setContextTags([])
    setAudioBlob(null); setQueuedId(null); setSelectedSpecies(null)
  }

  // The disabled analyse button always says what is missing.
  const missingReason = !file && !note.trim()
    ? t('catch.needPhotoOrNote')
    : preCheck && preCheck.verdict !== 'ok'
      ? t('catch.precheckBlocksHint')
      : null

  return (
    <>
      <LiveRegion />
      <div className="card">
        <h2>{t('catch.title')}</h2>

        {step === 'photo' && (
          /* Two columns from 900px up: photo left, note/context/analyse right.
             Stacked, this step ran well past a laptop viewport and the fisher
             had to scroll before seeing the Analyse button at all. One grid with
             a single gap also replaces the ad-hoc margins that made the spacing
             between sections uneven. */
          <div className="catch-step catch-step--capture">
            <div className="catch-step__col">
              <PhotoCapture preview={preview} busy={analyseMut.isPending}
                preCheck={preCheck} onFile={onFile} />
            </div>

            <div className="catch-step__col">
              <NoteField note={note} onNote={setNote} audioBlob={audioBlob}
                onAudio={setAudioBlob} announce={announce} />

              <ContextChips selected={contextTags} onChange={setContextTags} />

              <button className="primary analyse-btn"
                disabled={analyseMut.isPending || (!file && !note.trim())}
                onClick={startAnalysis}>
                {analyseMut.isPending ? (
                  <><span className="btn-spinner" aria-hidden="true" />{t('catch.identifying')}</>
                ) : t('catch.analyse')}
              </button>
              {missingReason && !analyseMut.isPending && (
                <p className="small disabled-reason">{missingReason}</p>
              )}

              {analyseMut.isPending && (
                <AnalyseProgress stage={progressStage} onCancel={cancelAnalysis} />
              )}

              {analyseMut.isError && <p className="banner danger">{t('common.error')}</p>}

              {analysis?.image_quality.status === 'invalid' && (
                <>
                  <p className="banner danger">
                    <strong>{t('catch.quality.invalid')}</strong><br />
                    {analysis.image_quality.warnings.join(', ')}
                  </p>
                  <button className="secondary" onClick={() => { setAnalysis(null); onFile(null) }}>
                    {t('catch.retake')}
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {step === 'suggestion' && analysis && (
          <ResultPanel analysis={analysis} species={allSpecies} selected={selectedSpecies}
            onSelect={setSelectedSpecies} onConfirm={() => setStep('measure')} />
        )}

        {step === 'measure' && (
          <>
            <p className="banner info">
              <Ruler size={16} aria-hidden="true" /> {t('catch.measureWhy')}
            </p>
            <label className="field" htmlFor="measure-length">{t('catch.measured')}
              <input id="measure-length" type="number" inputMode="decimal" min="1" max="400"
                value={length} onChange={(e) => setLength(e.target.value)} />
            </label>
            <label className="field" htmlFor="measure-count">{t('catch.count')}
              <input id="measure-count" type="number" inputMode="numeric" min="1"
                value={count} onChange={(e) => setCount(e.target.value)} />
            </label>
            <label className="field" htmlFor="measure-area">{t('catch.area')}
              <input id="measure-area" value={area} onChange={(e) => setArea(e.target.value)} />
            </label>

            {online ? (
              <>
                <button className="primary" disabled={confirmMut.isPending || !selectedSpecies}
                  onClick={() => confirmMut.mutate()}>
                  {confirmMut.isPending ? t('common.loading') : t('catch.saveCatch')}
                </button>
                {!selectedSpecies && <p className="small disabled-reason">{t('catch.needSpecies')}</p>}
              </>
            ) : (
              <>
                <p className="banner info">{t('catch.queueOffline')}</p>
                <button className="primary" onClick={queueOffline}>{t('catch.queueAction')}</button>
                {queuedId && (
                  <p className="banner info" role="status">
                    {t('catch.queued')} · <span className="mono">{queuedId}</span>
                  </p>
                )}
              </>
            )}
            {confirmMut.isError && <p className="banner danger">{t('common.error')}</p>}
          </>
        )}

        {step === 'result' && result && (
          <>
            <div className="result-header-row"><h1>{speciesLabel(result.species_id)}</h1></div>

            <div className="detail-grid">
              <div className="detail-item">
                <div className="detail-label">
                  {result.legal_check.status === 'allowed' ? <ShieldCheck size={14} aria-hidden="true" />
                    : result.legal_check.status === 'unknown' ? <ShieldQuestion size={14} aria-hidden="true" />
                      : <ShieldAlert size={14} aria-hidden="true" />}
                  {t('catch.regulatoryStatus')}
                </div>
                <div className={`detail-value legal-${result.legal_check.status}`}>
                  {t(`catch.rule.${result.legal_check.status}`)}
                </div>
              </div>
              {result.measured_length_cm != null && (
                <div className="detail-item">
                  <div className="detail-label"><Ruler size={14} aria-hidden="true" /> {t('catch.measuredSize')}</div>
                  <div className="detail-value mono">{result.measured_length_cm} cm</div>
                </div>
              )}
              {area && (
                <div className="detail-item">
                  <div className="detail-label"><MapPin size={14} aria-hidden="true" /> {t('catch.location')}</div>
                  <div className="detail-value">{area}</div>
                </div>
              )}
            </div>

            <div className="saved-receipt">
              <span className="saved-label">{t('catch.recordId')}</span>
              <span className="mono truncate">{result.catch_record_id}</span>
              <span className="badge sync-synced">{t('log.sync.synced')}</span>
            </div>

            {result.legal_check.rule && (
              <p className="small mono">
                {result.legal_check.rule} · {result.legal_check.source_id ?? '—'} · {result.legal_check.verification_status}
              </p>
            )}
            {result.legal_check.note && <p className="small">{result.legal_check.note}</p>}
            <p className="banner warn">{t('catch.rule.verify')}</p>
            {result.limitations.map((l) => (
              <p key={l} className={l.includes('Simulated') ? 'banner danger' : 'banner info'}>{l}</p>
            ))}

            <div className="result-actions">
              <button className="primary" onClick={resetForNext}>{t('catch.recordAnother')}</button>
              <Link to="/history" className="secondary">{t('catch.viewLog')}</Link>
            </div>

            {showCheckmark && (
              <div className="success-checkmark-layer" aria-hidden="true">
                <div className="success-checkmark"><Check size={40} /></div>
              </div>
            )}
          </>
        )}
      </div>
      {/* Replaces the old full-width info banner. Same job, less furniture, and
          the wording is the stricter AI disclaimer. The backend's own
          PERMANENT_LIMITATION is untouched and still rides on every analysis
          response, so the result step continues to show it verbatim. */}
      <p className="catch-ai-disclaimer">
        <strong>{t('catch.aiDisclaimerTitle')}</strong> {t('catch.aiDisclaimerBody')}
      </p>

      {/* Fixed to the viewport corner, so it sits outside the card rather than
          at the end of the flow. It is read-only by construction: the assistant
          cannot record or change the catch being entered above it. */}
      <AssistantBot />
    </>
  )
}
