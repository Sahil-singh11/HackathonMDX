/**
 * FormField + Input / Textarea / Select / DateField — FROZEN.
 *
 * FormField wires label, hint and error to the control PROPERLY:
 *   - label htmlFor -> control id
 *   - aria-describedby -> hint id and/or error id
 *   - aria-invalid + role="alert" on the error
 * so a screen reader announces the problem with the field, not somewhere else.
 *
 * FormField props:
 *   label     string    required — every input has a real label, no placeholders-as-labels
 *   children  (ctl) => ReactNode   render-prop receiving { id, describedBy, invalid }
 *   hint?     ReactNode
 *   error?    string    presence switches the field to the invalid state
 *   required? boolean
 *   id?       string    supply to control the id; otherwise auto-generated
 *
 * Input / Textarea / Select props: native attributes, plus
 *   data? boolean  render in the mono data role (IDs, weights, coordinates)
 *
 * Example:
 *   <FormField label="Measured length (cm)" hint="Use a ruler or mat" error={err}>
 *     {(c) => <Input {...c} type="number" inputMode="decimal" value={v} onChange={...} />}
 *   </FormField>
 */
import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'

export interface ControlProps {
  id: string
  'aria-describedby': string | undefined
  'aria-invalid': boolean | undefined
}

export function FormField({ label, hint, error, required, id: idProp, children }: {
  label: string
  hint?: ReactNode
  error?: string
  required?: boolean
  id?: string
  children: (control: ControlProps) => ReactNode
}) {
  const auto = useId()
  const id = idProp ?? `f-${auto}`
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="lk-field">
      <label className="lk-field__label" htmlFor={id}>
        {label}
        {required ? <span className="lk-field__req" aria-hidden="true">*</span> : null}
        {required ? <span className="lk-sr-only"> (required)</span> : null}
      </label>
      {hint ? <span className="lk-field__hint" id={hintId}>{hint}</span> : null}
      {children({ id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined })}
      {error ? <span className="lk-field__error" id={errorId} role="alert">{error}</span> : null}
    </div>
  )
}

export function Input({ data, className = '', ...rest }: InputHTMLAttributes<HTMLInputElement> & { data?: boolean }) {
  return <input className={`lk-input${data ? ' lk-input--data' : ''}${className ? ` ${className}` : ''}`} {...rest} />
}

export function Textarea({ className = '', ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`lk-textarea${className ? ` ${className}` : ''}`} {...rest} />
}

export function Select({ className = '', children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <span className="lk-select-wrap">
      <select className={`lk-select${className ? ` ${className}` : ''}`} {...rest}>{children}</select>
      <span className="lk-select-wrap__icon" aria-hidden="true">▾</span>
    </span>
  )
}

/**
 * DateField — a native date input in the mono data role.
 * Native is deliberate: it gives the platform date picker, works offline, and
 * is keyboard-accessible for free. Wrap it in your own lane if you need a range.
 */
export function DateField({ className = '', ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input type="date" className={`lk-input lk-input--data${className ? ` ${className}` : ''}`} {...rest} />
}
