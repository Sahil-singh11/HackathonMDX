import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useT } from '../i18n'
import { useAppStore } from '../store/app'

/**
 * Declaration — prepare a period of catches into a draft submission.
 *
 * WHAT THE REDESIGN CHANGED, and why. The page was a two-column split whose
 * right column existed only to hold a preview. Before a draft was prepared that
 * column rendered `decl.subtitle` — the SAME sentence already printed in the
 * left card — so the first thing a user saw was the same instruction twice, in
 * a 429x144 box. Measured with a real 12-catch draft the page ran to 1118px,
 * 206px past a 1080p viewport.
 *
 * It is now a single column that follows the actual workflow — choose a period,
 * review the draft, submit — because that is a linear task, not two things
 * happening side by side. The horizontal space the split was wasting goes to
 * the period row (three controls inline instead of two full-width date inputs
 * stacked) and to the review table.
 *
 * The catch list is capped with its own scroll. A declaration period can hold
 * any number of catches, so without a cap the page height is unbounded and
 * "fits the viewport" would depend on how much someone had fished that month.
 * The row count is shown in the header so the cap never hides how much is there.
 *
 * Nothing was removed: period pickers, prepare, the mock warning, the full
 * catch list with legal status, the PDF link, mock submit and the receipt are
 * all still here.
 */
export default function Declaration() {
  const t = useT()
  const { profileName, fishingArea } = useAppStore()
  const today = new Date().toISOString().slice(0, 10)
  const monthStart = today.slice(0, 8) + '01'
  const [start, setStart] = useState(monthStart)
  const [end, setEnd] = useState(today)
  const [draft, setDraft] = useState<Record<string, unknown> | null>(null)
  const [receipt, setReceipt] = useState<Record<string, unknown> | null>(null)

  const prepareMut = useMutation({
    mutationFn: () => api.prepareDeclaration({
      fisher_name: profileName, fishing_area: fishingArea, period_start: start, period_end: end,
    }),
    onSuccess: (d) => { setDraft(d); setReceipt(null) },
  })
  const submitMut = useMutation({
    mutationFn: () => api.mockSubmit(String(draft?.declaration_id)),
    onSuccess: setReceipt,
  })

  const catches = (draft?.catches as Record<string, unknown>[] | undefined) ?? []
  const totalFish = catches.reduce((n, c) => n + (Number(c.count) || 0), 0)
  const species = new Set(catches.map((c) => String(c.species_id))).size

  return (
    <div className="decl-page">
      <div className="card decl-card">
        <header className="decl-head">
          <div>
            <h2>{t('decl.title')}</h2>
            <p className="small decl-sub">{t('decl.subtitle')}</p>
          </div>
        </header>

        <p className="banner danger decl-mock"><strong>{t('decl.mockWarning')}</strong></p>

        {/* Three controls on one row. Two date inputs stretched to 429px each and
            stacked was the horizontal waste — a date field needs ~150px. */}
        <div className="decl-period">
          <label className="decl-field">
            <span>{t('decl.periodStart')}</span>
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="decl-field">
            <span>{t('decl.periodEnd')}</span>
            <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <button className="primary decl-prepare" disabled={prepareMut.isPending}
            onClick={() => prepareMut.mutate()}>
            {t('decl.prepare')}
          </button>
        </div>

        {prepareMut.isError && <p className="banner danger">{t('common.error')}</p>}

        {draft && (
          <section className={`decl-draft${receipt ? ' is-submitted' : ''}`}>
            <div className="decl-draft__head">
              <h3>{String(draft.mock_label)}</h3>
              <dl className="decl-figures">
                <div><dt>{t('decl.records')}</dt><dd className="mono">{catches.length}</dd></div>
                <div><dt>{t('decl.totalFish')}</dt><dd className="mono">{totalFish}</dd></div>
                <div><dt>{t('decl.speciesCount')}</dt><dd className="mono">{species}</dd></div>
              </dl>
            </div>

            {catches.length === 0 ? (
              <p className="small">{t('history.empty')}</p>
            ) : (
              /* Capped scroll: a period can contain any number of catches, so
                 without this the page height depends on how much was fished.
                 After submission the whole table folds — the receipt is the
                 outcome that matters then, and the rows stay one click away
                 rather than pushing it off screen. `open` is driven by state,
                 so a user can still expand it back. */
              <details className="decl-rows" open={!receipt}>
                <summary className="decl-rows__summary">
                  {t('decl.reviewRows').replace('{n}', String(catches.length))}
                </summary>
                <div className="decl-table-wrap" tabIndex={0}
                  role="region" aria-label={String(draft.mock_label)}>
                  <table className="decl-table">
                    <thead>
                      <tr>
                        <th scope="col">{t('decl.colSpecies')}</th>
                        <th scope="col">{t('decl.colCount')}</th>
                        <th scope="col">{t('decl.colDate')}</th>
                        <th scope="col">{t('decl.colLength')}</th>
                        <th scope="col">{t('decl.colStatus')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {catches.map((c, i) => (
                        <tr key={i}>
                          <td>{String(c.species_id)}</td>
                          <td className="mono">{String(c.count)}</td>
                          <td className="mono">{String(c.capture_date)}</td>
                          <td className="mono">{c.measured_length_cm ? `${c.measured_length_cm} cm` : '—'}</td>
                          <td>
                            <span className={`legal-${String(c.legal_status)}`}>
                              {t(`catch.rule.${String(c.legal_status)}`)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            )}

            <div className="decl-actions">
              <a className="primary" href={`/api/declarations/${String(draft.declaration_id)}/pdf`}
                target="_blank" rel="noreferrer">
                {t('decl.pdf')}
              </a>
              <button className="secondary" disabled={submitMut.isPending}
                onClick={() => submitMut.mutate()}>
                {t('decl.submitMock')}
              </button>
            </div>
            {submitMut.isError && <p className="banner danger">{t('common.error')}</p>}
          </section>
        )}

        {receipt && (
          <section className="decl-receipt">
            <h3>{t('decl.receipt')}</h3>
            <p className="mono decl-receipt__id">{String(receipt.mock_receipt_id)}</p>
            <p className="banner mockline">{String(receipt.notice)}</p>
          </section>
        )}
      </div>
    </div>
  )
}
