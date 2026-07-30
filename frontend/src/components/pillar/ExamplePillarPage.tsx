/* ExamplePillarPage — the reference page for this framework. Route: /pillars/_example
 *
 * WHAT THIS IS FOR. Every slot in use at once, every state reachable, so the
 * developer converting a real pillar can see what they are converting to
 * without running six pages. It converts nothing and imports nothing from a real
 * pillar — change a real page and this page does not move.
 *
 * THE NUMBERS ARE PLACEHOLDERS AND THE PAGE SAYS SO, on the page, in the answer
 * sentence. This app does not show invented figures without labelling them, and a
 * component gallery is not an exception — someone will screenshot it.
 */
import { useState } from 'react'
import { Chip } from '../ui'
import { Answer, BarComparison, FigureRow, Foldable, PillarPage } from './index'

const TONES = ['neutral', 'positive', 'caution'] as const
type Tone = typeof TONES[number]

const VISUAL_STATES = ['loaded', 'empty'] as const
type VisualState = typeof VISUAL_STATES[number]

export default function ExamplePillarPage() {
  const [tone, setTone] = useState<Tone>('neutral')
  const [visual, setVisual] = useState<VisualState>('loaded')

  return (
    <>
      {/* The control strip is part of the reference page, not part of the
          framework, so it sits outside PillarPage. */}
      <div className="lk-scope lkp-example-controls">
        <fieldset>
          <legend>Answer tone</legend>
          {TONES.map((tn) => (
            <Chip key={tn} selected={tn === tone} onToggle={() => setTone(tn)}>{tn}</Chip>
          ))}
        </fieldset>
        <fieldset>
          <legend>Visual state</legend>
          {VISUAL_STATES.map((v) => (
            <Chip key={v} selected={v === visual} onToggle={() => setVisual(v)}>{v}</Chip>
          ))}
        </fieldset>
      </div>

      <PillarPage
        title="Ocean-Based Renewable Energy"
        answer={(
          <Answer
            tone={tone}
            sentence="Placeholder figures on a reference page — every number here is made up. A real page says its answer in one sentence, like this one."
            hero={{ value: '25.5', unit: 'kW/m', caption: 'Wave power density at the strongest example site' }}
          />
        )}
        figures={(
          <FigureRow
            figures={[
              { label: 'Wave height', value: 2.2, unit: 'm' },
              { label: 'Wave period', value: 10.6, unit: 's' },
              { label: 'Wind speed', value: 12.2, unit: 'km/h', note: 'measured at 10 m' },
              { label: 'Sea temperature', value: null, unit: '°C' },
            ]}
          />
        )}
        visual={visual === 'empty' ? undefined : (
          <BarComparison
            caption="Bar length is relative to the strongest site shown, not an absolute scale."
            items={[
              { id: 'a', label: 'Example A', value: 2.2, unit: 'kW/m', detail: 'North · ~4 km offshore', highlight: true },
              { id: 'b', label: 'Example B', value: 2.0, unit: 'kW/m', detail: 'East · ~6 km offshore' },
              { id: 'c', label: 'Example C', value: 1.6, unit: 'kW/m', detail: 'South · ~2 km offshore' },
              { id: 'd', label: 'Example D', value: 1.1, unit: 'kW/m', detail: 'West · ~9 km offshore' },
            ]}
          />
        )}
        detail={(
          <Foldable title="Detail" hint="4 example rows">
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
          </Foldable>
        )}
        method={(
          <Foldable title="Method" tone="method" hint="Two formulas, computed before the page loads">
            <ul>
              <li>
                <strong>Wave power density</strong>: 0.49 x H^2 x T (H in m, T in s) — deep-water
                form, overstates power in shallow water.
              </li>
              <li>
                <strong>Wind power density</strong>: 0.5 x 1.225 x v^3 (v in m/s) — air density
                held constant.
              </li>
            </ul>
            <p>
              Prose can sit above the formulas when the method needs a sentence. Numbers are
              computed before this page renders and no written note can change one.
            </p>
          </Foldable>
        )}
        limits={(
          <Foldable title="Limits" tone="limits" hint="Forecast, not a survey">
            <ul>
              <li>A forecast window, not an observed record.</li>
              <li>No bathymetry, seabed conditions, cabling routes or grid connection cost.</li>
              <li>Not a yield assessment and not a siting recommendation.</li>
            </ul>
          </Foldable>
        )}
      />
    </>
  )
}
