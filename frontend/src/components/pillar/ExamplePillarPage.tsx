/* ExamplePillarPage — the reference page for this framework. Route: /pillars/_example
 *
 * WHAT THIS IS FOR. Every slot in use at once, every state reachable, so the
 * developer converting the real pillars can see what they are converting to
 * without running six pages. It converts nothing and imports nothing from a real
 * pillar — change a real page and this page does not move.
 *
 * THE NUMBERS ARE PLACEHOLDERS AND THE PAGE SAYS SO, on the page, in the answer
 * sentence. This app does not show invented figures without labelling them, and a
 * component gallery is not an exception — someone will screenshot it.
 *
 * The pillar switcher exists because the six accents are the one thing that
 * cannot be reviewed from a single render. It is a dev affordance, not a
 * suggestion that real pages get a switcher.
 *
 * NO MapLibre IMPORT HERE, deliberately: the map is a ~950 kB lazy chunk and
 * this page must not pull it in to demonstrate a container. The frame gives its
 * child a definite, absolutely-positioned box (see pillar.css) — the placeholder
 * below fills it exactly the way a map does.
 */
import { useState } from 'react'
import { Chip } from '../ui'
import {
  PillarPage, PillarAnswer, PillarFigures, PillarVisual,
  PillarDetail, PillarMethod, PillarLimits, PillarSource,
  type PillarDataKind, type PillarId, type PillarStatus,
} from './index'

const PILLARS: { id: PillarId; name: string }[] = [
  { id: 'fisheries', name: 'Sustainable Fisheries & Aquaculture' },
  { id: 'shipping', name: 'Marine Transport & Trade' },
  { id: 'tourism', name: 'Sustainable Ocean Tourism' },
  { id: 'energy', name: 'Ocean-Based Renewable Energy' },
  { id: 'finance', name: 'Blue Finance' },
  { id: 'biotech', name: 'Marine Biotechnology' },
]

const VISUAL_STATES = ['loaded', 'loading', 'empty'] as const
type VisualState = typeof VISUAL_STATES[number]

/** Stands in for a chart or a map. Fills the frame the way MapLibre will. */
function PlaceholderVisual() {
  return (
    <svg viewBox="0 0 320 180" preserveAspectRatio="none" role="img"
      aria-label="Placeholder standing in for a chart or map">
      <rect x="0" y="0" width="320" height="180" fill="var(--surface-sunken)" />
      <path d="M0 150 L60 120 L120 132 L180 84 L240 100 L320 56" fill="none"
        stroke="var(--lkp-accent)" strokeWidth="3" vectorEffect="non-scaling-stroke" />
      <line x1="0" y1="170" x2="320" y2="170" stroke="var(--border)" strokeWidth="1"
        vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

export default function ExamplePillarPage() {
  const [pillar, setPillar] = useState<PillarId>('energy')
  const [status, setStatus] = useState<PillarStatus>('live')
  const [visual, setVisual] = useState<VisualState>('loaded')
  const [kind, setKind] = useState<PillarDataKind>('live')

  const current = PILLARS.find((p) => p.id === pillar) ?? PILLARS[0]

  return (
    <>
      {/* The control strip is part of the reference page, not part of the
          framework, so it sits outside PillarPage and gets no accent. */}
      <div className="lk-scope lkp-example-controls">
        <fieldset>
          <legend>Pillar (accent)</legend>
          {PILLARS.map((p) => (
            <Chip key={p.id} selected={p.id === pillar} onToggle={() => setPillar(p.id)}>
              {p.id}
            </Chip>
          ))}
        </fieldset>
        <fieldset>
          <legend>Header status</legend>
          {(['live', 'cached', 'not-in-build'] as PillarStatus[]).map((s) => (
            <Chip key={s} selected={s === status} onToggle={() => setStatus(s)}>{s}</Chip>
          ))}
        </fieldset>
        <fieldset>
          <legend>Visual state</legend>
          {VISUAL_STATES.map((v) => (
            <Chip key={v} selected={v === visual} onToggle={() => setVisual(v)}>{v}</Chip>
          ))}
        </fieldset>
        <fieldset>
          <legend>Source data kind</legend>
          {(['live', 'cached', 'sample', 'synthetic'] as PillarDataKind[]).map((k) => (
            <Chip key={k} selected={k === kind} onToggle={() => setKind(k)}>{k}</Chip>
          ))}
        </fieldset>
      </div>

      <PillarPage
        pillar={pillar}
        pillarName={current.name}
        purpose="One sentence saying what this page tells you — not a paragraph, and not a description of the feature."
        status={status}

        answer={(
          <PillarAnswer
            sentence="Placeholder figures on a reference page — every number here is made up. A real page says its answer in one sentence, like this one."
            value="25.5"
            unit="kW/m"
            valueLabel="Wave power density at the strongest example site"
          />
        )}

        figures={(
          <PillarFigures
            figures={[
              { label: 'Wave height', value: '2.2', unit: 'm' },
              { label: 'Wave period', value: '10.6', unit: 's' },
              { label: 'Wind speed', value: '12.2', unit: 'km/h', hint: 'measured at 10 m' },
              { label: 'Sea temperature', value: '—', unit: '°C', hint: 'no reading' },
            ]}
          />
        )}

        visual={(
          <PillarVisual
            title="Visual slot"
            aspect="wide"
            loading={visual === 'loading'}
            empty={visual === 'empty'}
            emptyTitle="Nothing to plot yet"
            emptyBody="No readings have been collected for this area, so there is nothing to draw. Figures above are unaffected."
            caption="A caption belongs here in HTML, not inside the graphic, so it can be translated and read aloud."
          >
            <PlaceholderVisual />
          </PillarVisual>
        )}

        detail={(
          <PillarDetail summary="4 example rows">
            <table className="lkp-example-table">
              <caption>Placeholder rows, for layout only.</caption>
              <thead>
                <tr><th scope="col">Site</th><th scope="col">Wave</th><th scope="col">Wind</th></tr>
              </thead>
              <tbody>
                {[['Example A', '2.2 m', '12 km/h'], ['Example B', '2.0 m', '16 km/h'],
                  ['Example C', '1.6 m', '18 km/h'], ['Example D', '1.1 m', '27 km/h']].map((r) => (
                    <tr key={r[0]}><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>
                  ))}
              </tbody>
            </table>
          </PillarDetail>
        )}

        method={(
          <PillarMethod
            summary="Two formulas, computed before the page loads"
            formulas={[
              {
                name: 'Wave power density',
                expression: '0.49 x H^2 x T   (H in m, T in s)',
                note: 'Deep-water form. It overstates power in shallow water.',
              },
              {
                name: 'Wind power density',
                expression: '0.5 x 1.225 x v^3   (v in m/s)',
                note: 'Air density held constant.',
              },
            ]}
          >
            <p>
              Prose can sit above the formulas when the method needs a sentence.
              Numbers are computed before this page renders and no written note can
              change one.
            </p>
          </PillarMethod>
        )}

        limits={(
          <PillarLimits
            summary="Forecast, not a survey. Excludes seabed, grid access and consenting."
            items={[
              'A forecast window, not an observed record.',
              'No bathymetry, seabed conditions, cabling routes or grid connection cost.',
              'Not a yield assessment and not a siting recommendation.',
            ]}
          />
        )}

        source={(
          <PillarSource
            sourceName="Example source"
            sourceUrl="https://example.org"
            dataKind={kind}
            retrievedAt={new Date(Date.now() - 25 * 60_000).toISOString()}
          />
        )}
      />
    </>
  )
}
