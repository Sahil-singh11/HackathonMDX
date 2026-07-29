/**
 * Accessibility settings panel — FROZEN (Sahil's lane).
 *
 * Props:
 *   open      boolean
 *   onClose   () => void
 *
 * Exposes: theme (Day / Night / Sunlight), night vision, text size
 * (100/125/150%), reduce motion, disable background animation, and language.
 *
 * These are not decoration. The target user is on a boat: direct equatorial sun
 * washes out a normal light theme, a bright screen destroys night vision on a
 * pre-dawn crossing, and spray on the lens makes small text unreadable.
 */
import { Contrast, Eye, Languages, Moon, Sun, Type, Waves, Zap } from 'lucide-react'
import { Sheet } from '../ui'
import { Radio, Checkbox } from '../ui'
import { useTheme, THEME_LABELS, type Theme, type TextScale } from '../../theme'
import { useAppStore } from '../../store/app'
import { useOceanState } from '../ocean'

const THEME_ICONS: Record<Theme, typeof Sun> = { day: Sun, night: Moon, sunlight: Contrast }

const THEME_HINTS: Record<Theme, string> = {
  day: 'Normal daylight use.',
  night: 'Dark screen for night trips.',
  sunlight: 'Maximum contrast for direct sun on deck. Turns off animation.',
}

export function A11yPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const {
    theme, setTheme, nightVision, setNightVision,
    textScale, setTextScale, reduceMotion, setReduceMotion, systemReduceMotion,
  } = useTheme()
  const { language, setLanguage } = useAppStore()
  const { preference, blockedBy, setOceanEnabled } = useOceanState()

  return (
    <Sheet open={open} onClose={onClose} title="Display & accessibility">
      <fieldset style={{ border: 0, padding: 0, margin: '0 0 var(--sp-5)' }}>
        <legend className="lk-field__label" style={{ marginBottom: 'var(--sp-2)' }}>
          <Eye size={16} aria-hidden="true" /> Theme
        </legend>
        {(Object.keys(THEME_LABELS) as Theme[]).map((t) => {
          const Icon = THEME_ICONS[t]
          return (
            <Radio key={t} name="lk-theme" value={t} checked={theme === t}
              onChange={() => setTheme(t)}
              label={THEME_LABELS[t]}
              hint={<><Icon size={14} aria-hidden="true" /> {THEME_HINTS[t]}</>} />
          )
        })}
      </fieldset>

      {theme === 'night' && (
        <div style={{ marginBottom: 'var(--sp-5)' }}>
          <Checkbox checked={nightVision} onChange={(e) => setNightVision(e.target.checked)}
            label="Night vision"
            hint="Shifts the screen to deep red and cuts blue light so your eyes stay adapted to the dark." />
        </div>
      )}

      <fieldset style={{ border: 0, padding: 0, margin: '0 0 var(--sp-5)' }}>
        <legend className="lk-field__label" style={{ marginBottom: 'var(--sp-2)' }}>
          <Type size={16} aria-hidden="true" /> Text size
        </legend>
        {(['100', '125', '150'] as TextScale[]).map((s) => (
          <Radio key={s} name="lk-text-scale" value={s} checked={textScale === s}
            onChange={() => setTextScale(s)} label={`${s}%`} />
        ))}
      </fieldset>

      <fieldset style={{ border: 0, padding: 0, margin: '0 0 var(--sp-5)' }}>
        <legend className="lk-field__label" style={{ marginBottom: 'var(--sp-2)' }}>
          <Zap size={16} aria-hidden="true" /> Motion
        </legend>
        <Checkbox checked={reduceMotion} disabled={systemReduceMotion}
          onChange={(e) => setReduceMotion(e.target.checked)}
          label="Reduce motion"
          hint={systemReduceMotion
            ? 'Turned on by your device settings, so it cannot be switched off here.'
            : 'Removes animation and transitions.'} />
        {/* Dependent state: reduce-motion and Sunlight both force this off, so
            the control disables itself and SAYS why rather than sitting enabled
            while being silently overridden. */}
        <Checkbox checked={preference && !blockedBy} disabled={blockedBy !== null}
          onChange={(e) => setOceanEnabled(e.target.checked)}
          label="Background wave animation"
          hint={<><Waves size={14} aria-hidden="true" /> {
            blockedBy === 'reduce-motion'
              ? 'Turned off because Reduce motion is on.'
              : blockedBy === 'sunlight'
                ? 'Turned off in the Sunlight theme, where legibility comes first.'
                : 'The swell matches the current sea state — one wave cycle takes the real swell period. Turn it off to save battery.'
          }</>} />
      </fieldset>

      <fieldset style={{ border: 0, padding: 0 }}>
        <legend className="lk-field__label" style={{ marginBottom: 'var(--sp-2)' }}>
          <Languages size={16} aria-hidden="true" /> Language
        </legend>
        <Radio name="lk-lang" checked={language === 'mfe'} onChange={() => setLanguage('mfe')}
          label="Kreol Morisien" />
        <Radio name="lk-lang" checked={language === 'en'} onChange={() => setLanguage('en')}
          label="English" />
        {/* Français is in the design brief but there is no fr dictionary yet.
            Listing it as a dead option would be a lie, so it is deliberately
            omitted until frontend/src/i18n/fr.json exists. */}
      </fieldset>
    </Sheet>
  )
}
