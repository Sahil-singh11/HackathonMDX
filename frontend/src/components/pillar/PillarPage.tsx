/**
 * PillarPage — the shared presentation frame for every blue-economy pillar.
 *
 * WHAT PROBLEM THIS SOLVES. Each pillar surface had grown its own layout, so a
 * reader had to relearn where the conclusion was on every page, and the most
 * important sentence competed with a wall of figures. The order here is fixed and
 * deliberate:
 *
 *   1. ANSWER   one sentence, plus an optional hero number. The conclusion comes
 *               first; nobody should have to derive it from a table.
 *   2. FIGURES  up to four supporting numbers, mono, with units.
 *   3. VISUAL   a map or a comparison. Never the only route to the data.
 *   4. DETAIL   the full table or per-item breakdown. FOLDED by default.
 *   5. METHOD   how the numbers were produced. Folded — a strength, not clutter.
 *   6. LIMITS   what this does not cover. Folded, but never omitted and never
 *               summarised away.
 *
 * WHY DETAIL/METHOD/LIMITS FOLD RATHER THAN DISAPPEAR. This project's honesty
 * rules require the caveats to be present in full. Folding keeps them one click
 * away and complete, instead of the usual choice between burying them and
 * drowning the page. `Foldable` renders a real <details> element, so the content
 * is in the DOM, findable by browser search, and reachable by keyboard without
 * any JavaScript.
 *
 * Slots are ReactNode, so a pillar owner composes their own content and this
 * file never needs to know about vessels, dive sites or turbines.
 */
import type { ReactNode } from 'react'
import './pillar.css'

export interface PillarPageProps {
  /** Government pillar name, verbatim. */
  title: string
  /** The one-sentence conclusion. Use <Answer> to build it. */
  answer: ReactNode
  /** Up to four supporting figures. Use <FigureRow>. */
  figures?: ReactNode
  /** Map or comparison chart. */
  visual?: ReactNode
  /** Provenance / data-kind chip row, shown beside the figures. */
  chips?: ReactNode
  /** Folded sections. Use <Foldable>. */
  detail?: ReactNode
  method?: ReactNode
  limits?: ReactNode
}

export default function PillarPage({
  title, answer, figures, visual, chips, detail, method, limits,
}: PillarPageProps) {
  return (
    <div className="pil-page-frame">
      <h2 className="pil-frame__title">{title}</h2>

      <section className="pil-frame__answer" aria-label={title}>
        {answer}
      </section>

      {(figures || chips) && (
        <div className="pil-frame__figures">
          {figures}
          {chips && <div className="pil-frame__chips">{chips}</div>}
        </div>
      )}

      {visual && <div className="pil-frame__visual">{visual}</div>}

      {(detail || method || limits) && (
        <div className="pil-frame__folds">
          {detail}
          {method}
          {limits}
        </div>
      )}
    </div>
  )
}
