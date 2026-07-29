/**
 * Checkbox / Radio — FROZEN.
 * Props:
 *   label     string
 *   hint?     ReactNode
 *   ...native input attributes (checked, onChange, name, value, disabled)
 *
 * The whole row is the label, so the touch target is the full width — usable
 * with wet hands on a moving boat, not just the 24px box.
 */
import type { InputHTMLAttributes, ReactNode } from 'react'

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: string; hint?: ReactNode }

function Row({ type, label, hint, ...rest }: Props & { type: 'checkbox' | 'radio' }) {
  return (
    <label className="lk-choice">
      <input type={type} {...rest} />
      <span className="lk-choice__text">
        <span className="lk-choice__label">{label}</span>
        {hint ? <span className="lk-choice__hint">{hint}</span> : null}
      </span>
    </label>
  )
}

export function Checkbox(props: Props) { return <Row type="checkbox" {...props} /> }
export function Radio(props: Props) { return <Row type="radio" {...props} /> }
