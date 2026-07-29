/* Blue Finance pillar surface (Task 6b, Shirish's lane).
 *
 * Self-contained: wraps only frozen ui/ primitives and the shared
 * ProvenanceBadge, and is attached to /pillars/finance via PILLAR_SURFACES
 * in PillarDetail.tsx — the one shared-file edit that folder's own docstring
 * invites a pillar owner to make. Nothing else in that folder is touched.
 *
 * Never renders a pass/fail verdict on a bond: each criterion's status is
 * shown individually (met / unmet / indeterminate), backed by its evidence,
 * and the model's role (proposing fields, never judging eligibility) is
 * stated on the page, not just in a code comment.
 */
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, HelpCircle, Upload, XCircle } from 'lucide-react'
import { api, type FinanceCriteriaFinding, type FinanceResult } from '../../../api/client'
import { Badge, Button, Card, EmptyState, Spinner } from '../../ui'
import { useT } from '../../../i18n'
import { ProvenanceBadge } from '../../../pillars'
import './finance.css'

const STATUS_STYLE: Record<FinanceCriteriaFinding['status'], { tone: 'success' | 'danger' | 'warning'; icon: typeof CheckCircle2 }> = {
  met: { tone: 'success', icon: CheckCircle2 },
  unmet: { tone: 'danger', icon: XCircle },
  indeterminate: { tone: 'warning', icon: HelpCircle },
}

function FindingRow({ finding }: { finding: FinanceCriteriaFinding }) {
  const t = useT()
  const style = STATUS_STYLE[finding.status]
  const Icon = style.icon
  return (
    <li className="fin-finding">
      <div className="fin-finding__head">
        <Badge tone={style.tone} icon={<Icon size={14} aria-hidden="true" />}>
          {t(`finance.status.${finding.status}`)}
        </Badge>
        <strong>{finding.label}</strong>
        {finding.advisory_only && <span className="small">{t('finance.advisoryOnly')}</span>}
      </div>
      <p className="small">{finding.note}</p>
      {finding.evidence.map((f) => f.supported && (
        <p key={f.field} className="small fin-finding__span">
          {t('finance.page')} {f.page}: <span className="mono">&ldquo;{f.span}&rdquo;</span>
        </p>
      ))}
    </li>
  )
}

export default function FinancePanel() {
  const t = useT()
  const [sampleId, setSampleId] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<FinanceResult | null>(null)

  const { data: samplesData } = useQuery({ queryKey: ['financeSamples'], queryFn: api.financeSamples, retry: 1 })
  const samples = samplesData?.samples ?? []

  const analyseMut = useMutation({
    mutationFn: () => api.financeAnalyse(file ? { file } : { sampleId: sampleId ?? undefined }),
    onSuccess: setResult,
  })

  const disabled = analyseMut.isPending || (!file && !sampleId)

  return (
    <div className="fin-panel">
      <Card title={t('finance.title')}>
        <p className="small">{t('finance.intro')}</p>

        <fieldset className="fin-samples">
          <legend className="small" style={{ fontWeight: 700 }}>{t('finance.pickSample')}</legend>
          {samples.map((s) => (
            <label key={s.sample_id} className="fin-sample-option">
              <input type="radio" name="fin-sample" checked={sampleId === s.sample_id}
                onChange={() => { setSampleId(s.sample_id); setFile(null); setResult(null) }} />
              {s.label}
            </label>
          ))}
        </fieldset>

        <label className="fin-upload">
          <Upload size={16} aria-hidden="true" /> {t('finance.orUpload')}
          <input type="file" accept="application/pdf" className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0] ?? null; setFile(f); if (f) setSampleId(null); setResult(null) }} />
          {file && <span className="small mono">{file.name}</span>}
        </label>

        <Button variant="primary" disabled={disabled} loading={analyseMut.isPending} onClick={() => analyseMut.mutate()}>
          {t('finance.analyse')}
        </Button>

        {analyseMut.isError && (
          <p className="fin-error">
            <AlertTriangle size={16} aria-hidden="true" /> {t('finance.disabledOrError')}
          </p>
        )}
      </Card>

      {analyseMut.isPending && (
        <Card><Spinner label={t('finance.analysing')} /></Card>
      )}

      {result && (
        <>
          <Card title={t('finance.provenance')}>
            <ProvenanceBadge provenance={result.provenance} />
          </Card>

          <Card title={t('finance.findings')}>
            <p className="fin-overall-note">{result.overall_note}</p>
            {result.findings.length === 0 ? (
              <EmptyState icon={<HelpCircle size={40} aria-hidden="true" />}
                title={t('finance.noFindings')} body={t('finance.noFindingsBody')} />
            ) : (
              <ul className="fin-findings-list">
                {result.findings.map((f) => <FindingRow key={f.criterion_id} finding={f} />)}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
