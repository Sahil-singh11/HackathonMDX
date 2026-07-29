import { useMutation, useQuery } from '@tanstack/react-query'
import { Camera, CheckCircle2, Ruler } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, type AnalyseResponse, type ConfirmResponse, type SpeciesCandidate } from '../api/client'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'
import { enqueue } from '../utils/idb'

type Step = 'photo' | 'suggestion' | 'measure' | 'result'

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

  const { data: speciesData } = useQuery({ queryKey: ['species'], queryFn: api.species })
  const allSpecies: SpeciesCandidate[] = speciesData?.species ?? []

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

  return (
    <>
      <div className="card">
        <h2>{t('catch.title')}</h2>

        {step === 'photo' && (
          <>
            <button className="photo-drop" onClick={() => fileInput.current?.click()} type="button">
              <Camera size={34} aria-hidden="true" />
              {t('catch.takePhoto')}
              <span className="small">{t('catch.photoTips')}</span>
            </button>
            <input ref={fileInput} type="file" accept="image/*" capture="environment" className="sr-only"
              aria-label={t('catch.takePhoto')}
              onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
            {preview && <img src={preview} alt="preview" className="photo-preview" style={{ marginTop: '0.6rem' }} />}
            <label className="field">{t('catch.note')}
              <textarea rows={2} value={note} placeholder={t('catch.notePlaceholder')}
                onChange={(e) => setNote(e.target.value)} />
            </label>
            <button className="primary" disabled={analyseMut.isPending || (!file && !note)}
              onClick={() => analyseMut.mutate()}>
              {analyseMut.isPending ? t('catch.analysing') : t('catch.analyse')}
            </button>
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
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
              <span className={`badge quality-${analysis.image_quality.status}`}>
                {t(`catch.quality.${analysis.image_quality.status}`)}
              </span>
              <span className={`badge conf-${analysis.confidence_label}`}>
                {t(`catch.confidence.${analysis.confidence_label}`)}
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
              <p className="banner warn">{t('catch.estimatedSize')}: ~{analysis.estimated_size_unverified_cm} cm</p>
            )}
            <h3>{t('catch.confirmPrompt')}</h3>
            {allSpecies.map((sp) => (
              <button key={sp.species_id} className="species-option" type="button"
                aria-pressed={selectedSpecies === sp.species_id}
                onClick={() => setSelectedSpecies(sp.species_id)}>
                <CheckCircle2 size={20} aria-hidden="true"
                  color={selectedSpecies === sp.species_id ? 'var(--coral)' : '#c4cddb'} />
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
            <h3>{t('catch.rule.title')}</h3>
            <p className={`legal-${result.legal_check.status}`} style={{ fontSize: '1.1rem' }}>
              {t(`catch.rule.${result.legal_check.status}`)}
            </p>
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
            <p className="banner info"><strong>{t('catch.saved')}</strong> — {result.species_id}, {result.count}×
              {result.measured_length_cm ? `, ${result.measured_length_cm} cm` : ''} ({result.capture_date})</p>
            <button className="secondary" onClick={() => {
              setStep('photo'); setAnalysis(null); setResult(null); onFile(null); setNote(''); setLength('')
            }}>{t('nav.catch')}</button>
          </>
        )}
      </div>
      <p className="banner info">{t('limitation.permanent')}</p>
    </>
  )
}
