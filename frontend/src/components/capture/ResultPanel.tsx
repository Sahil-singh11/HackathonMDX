/* Species result panel (Lane B) — the advisory surface.
 *
 * Design rule that governs this file: the model is ADVISORY. Nothing here may
 * read as a verdict. That means:
 *   - confidence is a named band (high / moderate / low), never a bare percentage
 *   - the top alternatives are always visible and always one tap away
 *   - "None of these" is a first-class path, not a hidden fallback
 *   - on low confidence the manual path is promoted above the suggestion
 *   - nothing is saved until the fisher explicitly confirms
 *
 * Props:
 *   analysis   AnalyseResponse
 *   species    SpeciesCandidate[]        full catalogue
 *   selected   string | null             confirmed species id
 *   onSelect   (id: string|null) => void
 *   onConfirm  () => void
 */
import { AlertTriangle, CheckCircle2, Ruler } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { AnalyseResponse, SpeciesCandidate } from '../../api/client'
import { useT } from '../../i18n'
import { useAppStore } from '../../store/app'

interface Props {
  analysis: AnalyseResponse
  species: SpeciesCandidate[]
  selected: string | null
  onSelect: (id: string | null) => void
  onConfirm: () => void
}

/* The API returns one suggestion plus a confidence band, not a ranked list, so
 * "alternatives" are the rest of the catalogue. Kept to 3 to stay glanceable;
 * the full list is one tap away behind "None of these". */
const ALTERNATIVES_SHOWN = 3

export default function ResultPanel({ analysis, species, selected, onSelect, onConfirm }: Props) {
  const t = useT()
  const { language } = useAppStore()
  const suggestedId = analysis.species_suggestion.species_id
  const lowConfidence = analysis.confidence_label === 'low'
  const [manualOpen, setManualOpen] = useState(lowConfidence)

  const suggested = species.find((s) => s.species_id === suggestedId) ?? null
  const alternatives = useMemo(
    () => species.filter((s) => s.species_id !== suggestedId).slice(0, ALTERNATIVES_SHOWN),
    [species, suggestedId],
  )

  const reply = language === 'mfe' && analysis.reply_morisyen ? analysis.reply_morisyen : analysis.reply

  const optionRow = (sp: SpeciesCandidate) => (
    <button key={sp.species_id} className="species-option" type="button"
      aria-pressed={selected === sp.species_id}
      onClick={() => onSelect(sp.species_id)}>
      <CheckCircle2 size={20} aria-hidden="true"
        color={selected === sp.species_id ? 'var(--primary-coral)' : 'var(--border-subtle)'} />
      <span className="names">
        <span className="mfe-name">
          {sp.morisyen}{sp.morisyen_status !== 'human_verified' ? ' *' : ''} — {sp.english}
        </span>
        <span className="sci">{sp.scientific}</span>
      </span>
    </button>
  )

  return (
    <div className="result-panel">
      {/* Low confidence leads with the manual path, not with the guess. */}
      {lowConfidence && (
        <div className="banner warn low-confidence-lead" role="status">
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>{t('catch.lowConfidenceTitle')}</strong>
            <p>{t('catch.lowConfidenceBody')}</p>
          </div>
        </div>
      )}

      <div className="result-header-row">
        <h1>{suggested?.english ?? analysis.species_suggestion.english ?? t('catch.suggestion')}</h1>
        <span className={`badge conf-${analysis.confidence_label}`}>
          {t(`catch.confidence.${analysis.confidence_label}`)}
        </span>
      </div>
      <p className="small advisory-line">{t('catch.advisoryLine')}</p>

      <div className="result-badges">
        <span className={`badge quality-${analysis.image_quality.status}`}>
          {t(`catch.quality.${analysis.image_quality.status}`)}
        </span>
        <span className={`badge ${analysis.provider.mode === 'mock' ? 'mock' : 'hosted'}`}>
          {t(`common.provider.${analysis.provider.mode}`)} · <span className="mono">{analysis.provider.latency_ms} ms</span>
        </span>
      </div>

      {analysis.image_quality.warnings.length > 0 && (
        <p className="banner warn">{analysis.image_quality.warnings.join(', ')}</p>
      )}
      {reply && <p>{reply}</p>}

      {analysis.visible_characteristics.length > 0 && (
        <>
          <h3 className="section-label">{t('catch.whyThis')}</h3>
          <ul className="small">
            {analysis.visible_characteristics.map((c) => <li key={c}>{c}</li>)}
          </ul>
        </>
      )}

      {/* The AI's size estimate is shown for context only and is never sent to the
         rule engine — only a measured length is, on the next step. */}
      {analysis.estimated_size_unverified_cm != null && (
        <p className="banner warn">
          <Ruler size={16} aria-hidden="true" />
          {t('catch.estimatedSize')}: <span className="mono">~{analysis.estimated_size_unverified_cm} cm</span>
          <span className="small"> — {t('catch.estimatedSizeCaveat')}</span>
        </p>
      )}

      <h3 className="section-label">{t('catch.confirmPrompt')}</h3>

      {suggested && !lowConfidence && (
        <div className="option-group">
          <p className="option-group-label">{t('catch.suggestedLabel')}</p>
          {optionRow(suggested)}
        </div>
      )}

      <div className="option-group">
        <p className="option-group-label">{t('catch.alternativesLabel')}</p>
        {(lowConfidence && suggested ? [suggested, ...alternatives] : alternatives).map(optionRow)}
      </div>

      <button type="button" className="none-of-these" aria-expanded={manualOpen}
        onClick={() => setManualOpen((v) => !v)}>
        {t('catch.noneOfThese')}
      </button>

      {manualOpen && (
        <div className="option-group manual-group">
          <p className="option-group-label">{t('catch.manualLabel')}</p>
          {species.map(optionRow)}
        </div>
      )}

      <p className="small">{t('catch.morisyenPending')}</p>

      <button className="primary" disabled={!selected} onClick={onConfirm}>
        {selected ? t('catch.confirm') : t('catch.confirmDisabled')}
      </button>
    </div>
  )
}
