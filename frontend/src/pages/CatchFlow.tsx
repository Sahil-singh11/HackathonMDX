import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Camera, Check, CheckCircle2, MapPin, Mic, Ruler, RotateCcw,
  ShieldAlert, ShieldCheck, ShieldQuestion,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type AnalyseResponse, type ConfirmResponse, type SpeciesCandidate } from '../api/client'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'
import { enqueue } from '../utils/idb'

type Step = 'photo' | 'suggestion' | 'measure' | 'result'

interface SpeechRecognitionResultLike { transcript: string }
interface SpeechRecognitionEventLike { results: ArrayLike<ArrayLike<SpeechRecognitionResultLike>> }
interface SpeechRecognitionLike {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as { webkitSpeechRecognition?: SpeechRecognitionCtor; SpeechRecognition?: SpeechRecognitionCtor }
  return w.webkitSpeechRecognition ?? w.SpeechRecognition ?? null
}

const QUICK_TAG_KEYS = ['catch.tag.reef', 'catch.tag.deepSea', 'catch.tag.morning', 'catch.tag.evening', 'catch.tag.nearShore']
const AVATAR_HUES = ['avatar-hue-0', 'avatar-hue-1', 'avatar-hue-2']

export default function CatchFlow() {
  const t = useT()
  const { language, fishingArea, online, setLastAnalysis } = useAppStore()
  const [step, setStep] = useState<Step>('photo')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [analysis, setAnalysis] = useState<AnalyseResponse | null>(null)
  const [selectedSpecies, setSelectedSpecies] = useState<string | null>(null)
  const [length, setLength] = useState('')
  const [count, setCount] = useState('1')
  const [area, setArea] = useState(fishingArea)
  const [result, setResult] = useState<ConfirmResponse | null>(null)
  const [queuedMsg, setQueuedMsg] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const [micActive, setMicActive] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const speechSupported = getSpeechRecognitionCtor() != null

  const [progressStep, setProgressStep] = useState(0)
  const [showCheckmark, setShowCheckmark] = useState(false)

  const { data: speciesData } = useQuery({ queryKey: ['species'], queryFn: api.species })
  const allSpecies: SpeciesCandidate[] = speciesData?.species ?? []
  const speciesById = new Map<string, SpeciesCandidate>(allSpecies.map((s) => [s.species_id, s]))
  const speciesLabel = (id: string) => speciesById.get(id)?.english ?? id

  const { data: recentCatchesData } = useQuery({ queryKey: ['catches'], queryFn: api.catches })
  const recentCatches = (recentCatchesData?.catches ?? []).slice(0, 5)

  const analyseMut = useMutation({
    mutationFn: async () => {
      const form = new FormData()
      if (file) form.append('image', file)
      if (note) form.append('note', note)
      form.append('language', language)
      return api.analyse(form)
    },
    onSuccess: (data) => {
      setAnalysis(data)
      setLastAnalysis(data.provider, data.function_trace)
      if (data.image_quality.status !== 'invalid') {
        setSelectedSpecies(data.species_suggestion.species_id)
        setStep('suggestion')
      }
    },
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
    onSuccess: (data) => { setResult(data); setStep('result') },
  })

  const onFile = (f: File | null) => {
    setFile(f)
    setPreview(f ? URL.createObjectURL(f) : null)
  }

  const queueOffline = async () => {
    if (!selectedSpecies) return
    await enqueue({
      species_id: selectedSpecies,
      measured_length_cm: length ? parseFloat(length) : null,
      count: parseInt(count || '1', 10),
      capture_date: new Date().toISOString().slice(0, 10),
      fishing_area: area,
      queued_at: new Date().toISOString(),
    })
    setQueuedMsg(true)
  }

  const reply = analysis ? (language === 'mfe' && analysis.reply_morisyen ? analysis.reply_morisyen : analysis.reply) : ''

  // Simulated staged progress for the analyse call: the backend does this as one
  // opaque request with no granular phase events, so this is a perceived-progress
  // indicator, not a readout of real server-side telemetry.
  useEffect(() => {
    if (!analyseMut.isPending) { setProgressStep(0); return }
    const t1 = setTimeout(() => setProgressStep(1), 1200)
    const t2 = setTimeout(() => setProgressStep(2), 2600)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [analyseMut.isPending])

  useEffect(() => {
    if (step !== 'result') return
    setShowCheckmark(true)
    const timer = setTimeout(() => setShowCheckmark(false), 900)
    return () => clearTimeout(timer)
  }, [step])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [note])

  const toggleMic = () => {
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) return
    if (micActive) {
      recognitionRef.current?.stop()
      return
    }
    const recognition = new Ctor()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = language === 'mfe' ? 'fr-FR' : 'en-US'
    recognition.onresult = (ev) => {
      const transcript = ev.results[ev.results.length - 1][0].transcript
      setNote((prev) => (prev ? `${prev} ${transcript}` : transcript))
    }
    recognition.onend = () => setMicActive(false)
    recognitionRef.current = recognition
    recognition.start()
    setMicActive(true)
  }

  const addTag = (label: string) => {
    setNote((prev) => (prev ? `${prev}, ${label}` : label))
  }

  const progressSteps = [
    { key: 'scan', label: t('catch.progress.scan') },
    { key: 'match', label: t('catch.progress.match') },
    { key: 'rules', label: t('catch.progress.rules') },
  ]

  return (
    <>
      <div className="card">
        <h2>{t('catch.title')}</h2>

        {step === 'photo' && (
          <>
            <div className={`catch-photo-zone${preview ? ' has-image' : ''}`}
              onClick={() => { if (!preview) fileInput.current?.click() }}>
              {preview ? (
                <>
                  <img src={preview} alt="preview" className="photo-fill" />
                  {analyseMut.isPending && <div className="photo-shimmer" aria-hidden="true" />}
                  <button type="button" className="photo-retake-btn" aria-label={t('catch.retake')}
                    onClick={(e) => { e.stopPropagation(); onFile(null); setAnalysis(null) }}>
                    <RotateCcw size={20} aria-hidden="true" />
                  </button>
                </>
              ) : (
                <div className="catch-photo-empty">
                  <Camera size={48} className="photo-icon" aria-hidden="true" />
                  <h2>{t('catch.takePhoto')}</h2>
                  <div className="photo-tip-row">
                    <span className="photo-tip-chip">{t('catch.tip.goodLight')}</span>
                    <span className="photo-tip-chip">{t('catch.tip.wholeFish')}</span>
                    <span className="photo-tip-chip">{t('catch.tip.addRuler')}</span>
                    <span className="photo-tip-chip">{t('catch.tip.avoidFaces')}</span>
                  </div>
                </div>
              )}
            </div>
            <input ref={fileInput} type="file" accept="image/*" capture="environment" className="sr-only"
              aria-label={t('catch.takePhoto')}
              onChange={(e) => onFile(e.target.files?.[0] ?? null)} />

            {recentCatches.length > 0 && (
              <>
                <div className="recent-thumbs-label">{t('catch.recent')}</div>
                <div className="recent-thumbs-row">
                  {recentCatches.map((c, i) => (
                    <div key={String(c.id)} className={`recent-thumb ${AVATAR_HUES[i % AVATAR_HUES.length]}`}
                      title={speciesLabel(String(c.species_id))}>
                      {speciesLabel(String(c.species_id)).slice(0, 2).toUpperCase()}
                    </div>
                  ))}
                </div>
              </>
            )}

            <label className="field">{t('catch.note')}
              <div className="note-wrap">
                <textarea ref={textareaRef} rows={2} value={note} placeholder={t('catch.notePlaceholder')}
                  onChange={(e) => setNote(e.target.value)} />
                {speechSupported && (
                  <button type="button" className={`mic-btn${micActive ? ' recording' : ''}`}
                    aria-label={t('catch.voiceInput')} onClick={toggleMic}>
                    <Mic size={18} aria-hidden="true" />
                  </button>
                )}
              </div>
            </label>

            <div className="quick-tags-row">
              {QUICK_TAG_KEYS.map((key) => (
                <button key={key} type="button" className="quick-tag" onClick={() => addTag(t(key))}>
                  {t(key)}
                </button>
              ))}
            </div>

            <button className="primary analyse-btn" disabled={analyseMut.isPending || (!file && !note)}
              onClick={() => analyseMut.mutate()}>
              {analyseMut.isPending ? (
                <>
                  <span className="btn-spinner" aria-hidden="true" />
                  {t('catch.identifying')}
                </>
              ) : t('catch.analyse')}
            </button>

            {analyseMut.isPending && (
              <div className="progress-tracker">
                {progressSteps.map((s, i) => (
                  <div key={s.key}
                    className={`progress-step${i === progressStep ? ' active' : i < progressStep ? ' done' : ''}`}>
                    {i < progressStep ? <Check size={14} aria-hidden="true" /> : <span className="dot" />}
                    {s.label}
                  </div>
                ))}
              </div>
            )}

            {analyseMut.isError && <p className="banner danger">{t('common.error')}</p>}
            {analysis && analysis.image_quality.status === 'invalid' && (
              <>
                <p className="banner danger">
                  <strong>{t('catch.quality.invalid')}</strong><br />
                  {analysis.image_quality.warnings.join(', ')}<br />{reply}
                </p>
                <button className="secondary" onClick={() => { setAnalysis(null); onFile(null) }}>
                  {t('catch.retake')}
                </button>
              </>
            )}
          </>
        )}

        {step === 'suggestion' && analysis && (
          <>
            <div className="result-header-row">
              <h1>{analysis.species_suggestion.english ?? analysis.species_suggestion.morisyen ?? t('catch.suggestion')}</h1>
              <span className={`badge conf-${analysis.confidence_label}`}>
                {t(`catch.confidence.${analysis.confidence_label}`)}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', margin: 'var(--space-3) 0' }}>
              <span className={`badge quality-${analysis.image_quality.status}`}>
                {t(`catch.quality.${analysis.image_quality.status}`)}
              </span>
              <span className={`badge ${analysis.provider.mode === 'mock' ? 'mock' : 'hosted'}`}>
                {t(`common.provider.${analysis.provider.mode}`)} · {analysis.provider.latency_ms} ms
              </span>
            </div>
            {analysis.image_quality.warnings.length > 0 && (
              <p className="banner warn">{analysis.image_quality.warnings.join(', ')}</p>
            )}
            {reply && <p>{reply}</p>}
            {analysis.visible_characteristics.length > 0 && (
              <ul className="small">
                {analysis.visible_characteristics.map((c) => <li key={c}>{c}</li>)}
              </ul>
            )}
            {analysis.estimated_size_unverified_cm != null && (
              <p className="banner warn">
                <Ruler size={16} aria-hidden="true" /> {t('catch.estimatedSize')}: ~{analysis.estimated_size_unverified_cm} cm
              </p>
            )}
            <h3>{t('catch.confirmPrompt')}</h3>
            {allSpecies.map((sp) => (
              <button key={sp.species_id} className="species-option" type="button"
                aria-pressed={selectedSpecies === sp.species_id}
                onClick={() => setSelectedSpecies(sp.species_id)}>
                <CheckCircle2 size={20} aria-hidden="true"
                  color={selectedSpecies === sp.species_id ? 'var(--primary-coral)' : 'var(--border-subtle)'} />
                <span className="names">
                  <span className="mfe-name">{sp.morisyen}{sp.morisyen_status !== 'human_verified' ? ' *' : ''} — {sp.english}</span>
                  <span className="sci">{sp.scientific}</span>
                </span>
              </button>
            ))}
            <p className="small">* Morisyen name pending human verification</p>
            <button className="primary" disabled={!selectedSpecies} onClick={() => setStep('measure')}>
              {t('catch.confirm')}
            </button>
          </>
        )}

        {step === 'measure' && (
          <>
            <p className="banner info"><Ruler size={16} aria-hidden="true" /> {t('catch.measured')}</p>
            <label className="field">{t('catch.measured')}
              <input type="number" inputMode="decimal" min="1" max="400" value={length}
                onChange={(e) => setLength(e.target.value)} />
            </label>
            <label className="field">{t('catch.count')}
              <input type="number" inputMode="numeric" min="1" value={count}
                onChange={(e) => setCount(e.target.value)} />
            </label>
            <label className="field">{t('catch.area')}
              <input value={area} onChange={(e) => setArea(e.target.value)} />
            </label>
            {online ? (
              <button className="primary" disabled={confirmMut.isPending || !selectedSpecies}
                onClick={() => confirmMut.mutate()}>
                {t('catch.saveCatch')}
              </button>
            ) : (
              <>
                <p className="banner warn">{t('catch.queueOffline')}</p>
                <button className="primary" onClick={queueOffline}>{t('nav.queue')}</button>
                {queuedMsg && <p className="banner info">{t('catch.queued')}</p>}
              </>
            )}
            {confirmMut.isError && <p className="banner danger">{t('common.error')}</p>}
          </>
        )}

        {step === 'result' && result && (
          <>
            <div className="result-header-row">
              <h1>{speciesLabel(result.species_id)}</h1>
            </div>

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
                  <div className="detail-value">{result.measured_length_cm} cm</div>
                </div>
              )}
              {area && (
                <div className="detail-item">
                  <div className="detail-label"><MapPin size={14} aria-hidden="true" /> {t('catch.location')}</div>
                  <div className="detail-value">{area}</div>
                </div>
              )}
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
              <button className="primary" onClick={() => {
                setStep('photo'); setAnalysis(null); setResult(null); onFile(null); setNote(''); setLength('')
              }}>{t('catch.recordAnother')}</button>
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
      <p className="banner info">{t('limitation.permanent')}</p>
    </>
  )
}
