/**
 * Spinner — FROZEN.
 * Props: label? string (default 'Loading') — announced to screen readers; pass
 *        '' when the spinner sits inside a button that already has a label.
 *        size? string CSS length (default '1.25em', inherits font size).
 */
export function Spinner({ label = 'Loading', size }: { label?: string; size?: string }) {
  return (
    <>
      <span className="lk-spinner" style={size ? { width: size, height: size } : undefined} aria-hidden="true" />
      {label ? <span className="lk-sr-only">{label}</span> : null}
    </>
  )
}
