/* Workstream 2 — ProvenanceBadge.
 *
 * The honesty component for the whole pillar phase. Every pillar surface renders
 * this next to its output, so a viewer can always tell what they are looking at.
 *
 * Two rules drive the design:
 *
 * 1. VISUAL WEIGHT SCALES WITH RISK. `live` and `cached` are quiet — they are
 *    the normal, trustworthy states and shouting about them would train people
 *    to ignore the badge. `sample` is clearly marked. `synthetic` is loud and
 *    unmissable, because presenting generated numbers as observations is the
 *    single worst thing this platform could do in front of a judge or an officer.
 *
 * 2. coverage_note IS ALWAYS VISIBLE. Never a tooltip, never an accordion,
 *    never truncated. What the data does NOT cover is the part people skip, so
 *    it is the part that must not be skippable.
 *
 * Props:
 *   provenance  DataProvenance  the backend's block, rendered as-is
 *   compact?    boolean         index-card variant: kind + source only, no note
 */
import { AlertTriangle, Beaker, Clock, FlaskConical, Radio } from 'lucide-react'
import { Badge } from '../components/ui'
import { useT } from '../i18n'
import type { DataKind, DataProvenance } from './types'

interface Props {
  provenance: DataProvenance
  compact?: boolean
}

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger'

/* Colour is never the only signal: every state carries an icon AND a text
 * label AND (for sample/synthetic) a heavier container. */
const KIND_STYLE: Record<DataKind, { tone: Tone; icon: typeof Radio; loud: boolean }> = {
  live: { tone: 'success', icon: Radio, loud: false },
  cached: { tone: 'neutral', icon: Clock, loud: false },
  sample: { tone: 'warning', icon: Beaker, loud: true },
  synthetic: { tone: 'danger', icon: FlaskConical, loud: true },
}

/** Human-readable age, e.g. "25 min ago". Staleness is the point of `cached`. */
function ageLabel(retrievedAt: string, t: (k: string) => string): string | null {
  const then = Date.parse(retrievedAt)
  if (Number.isNaN(then)) return null
  const mins = Math.floor((Date.now() - then) / 60000)
  if (mins < 1) return t('pillars.age.justNow')
  if (mins < 60) return `${mins} ${t('pillars.age.minAgo')}`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} ${t('pillars.age.hoursAgo')}`
  return `${Math.floor(hours / 24)} ${t('pillars.age.daysAgo')}`
}

/** Registry key -> the label the app already shows for that provider. */
const PROVIDER_LABEL: Record<string, string> = {
  gemma_hosted: 'common.provider.hosted',
  gemma_local: 'common.provider.local',
  mock: 'common.provider.mock',
}

export function providerLabel(id: string, t: (k: string) => string): string {
  if (!id || id === 'none') return t('pillars.modelProviderNone')
  const key = PROVIDER_LABEL[id]
  // No raw key ever reaches the page: an unmapped provider is described, not
  // printed. If a new provider is added, this reads as "a language model" until
  // someone gives it a label — wrong-but-harmless rather than leaking an id.
  return key ? t(key) : t('pillars.modelProviderGeneric')
}

export default function ProvenanceBadge({ provenance, compact = false }: Props) {
  const t = useT()
  const { data_kind, source_name, source_url, retrieved_at, model_provider, coverage_note } = provenance
  const style = KIND_STYLE[data_kind] ?? KIND_STYLE.synthetic
  const Icon = style.icon
  const age = ageLabel(retrieved_at, t)

  const kindBadge = (
    <Badge tone={style.tone} icon={<Icon size={14} aria-hidden="true" />}>
      {t(`pillars.kind.${data_kind}`)}
    </Badge>
  )

  if (compact) {
    return (
      <span className="pil-prov pil-prov--compact">
        {kindBadge}
        <span className="pil-prov__src">{source_name}</span>
      </span>
    )
  }

  return (
    <div className={`pil-prov pil-prov--${data_kind}${style.loud ? ' pil-prov--loud' : ''}`}>
      <div className="pil-prov__head">
        {kindBadge}
        <span className="pil-prov__meta">
          {source_url
            ? <a href={source_url} target="_blank" rel="noreferrer">{source_name}</a>
            : <span>{source_name}</span>}
          {age && <> · <span className="pil-data">{age}</span></>}
        </span>
      </div>

      {/* The loud states say plainly what they are, in prose, above the note. */}
      {data_kind === 'synthetic' && (
        <p className="pil-prov__alarm">
          <AlertTriangle size={16} aria-hidden="true" /> {t('pillars.kind.syntheticWarning')}
        </p>
      )}
      {data_kind === 'sample' && (
        <p className="pil-prov__alarm">
          <AlertTriangle size={16} aria-hidden="true" /> {t('pillars.kind.sampleWarning')}
        </p>
      )}

      {/* ALWAYS VISIBLE. Do not move this behind a disclosure. */}
      <p className="pil-prov__coverage">
        <strong>{t('pillars.coverage')}</strong>{' '}
        {coverage_note || (
          <em className="pil-prov__missing">{t('pillars.coverageMissing')}</em>
        )}
      </p>

      {/* WHICH model answered is an honesty requirement; its INTERNAL IDENTIFIER
          is not. "gemma_hosted" / "gemma_local" are registry keys that leaked
          onto the page as-is. They map to the labels the app already uses in its
          header, so the disclosure survives and the developer token does not.
          Anything unrecognised falls back to a neutral phrase rather than
          printing a raw key. */}
      <p className="pil-prov__provider">
        {t('pillars.modelProvider')} {providerLabel(model_provider, t)}
      </p>
    </div>
  )
}
