/* Multi-select context chips (Lane B).
 *
 * Reef / Deep sea / Morning / Evening / Near shore. These are real toggles that
 * carry state, not buttons that paste text into the note field: the selection is
 * submitted alongside the note so context survives even when the note is empty.
 *
 * Props:
 *   selected  string[]                 currently selected chip keys
 *   onChange  (keys: string[]) => void
 */
import { Check } from 'lucide-react'
import { useT } from '../../i18n'

export const CONTEXT_CHIP_KEYS = [
  'catch.tag.reef',
  'catch.tag.deepSea',
  'catch.tag.morning',
  'catch.tag.evening',
  'catch.tag.nearShore',
] as const

interface Props {
  selected: string[]
  onChange: (keys: string[]) => void
}

export default function ContextChips({ selected, onChange }: Props) {
  const t = useT()

  const toggle = (key: string) => {
    onChange(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key])
  }

  return (
    <fieldset className="context-chips">
      <legend>{t('catch.context')}</legend>
      <div className="context-chips-row">
        {CONTEXT_CHIP_KEYS.map((key) => {
          const on = selected.includes(key)
          return (
            <button key={key} type="button" className={`context-chip${on ? ' selected' : ''}`}
              aria-pressed={on} onClick={() => toggle(key)}>
              {/* Never colour-only: selected chips also gain a tick and a heavier border. */}
              <span className="chip-tick" aria-hidden="true">{on ? <Check size={16} /> : null}</span>
              {t(key)}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}
