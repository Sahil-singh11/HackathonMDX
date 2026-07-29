/**
 * Divider — FROZEN.
 * Props: tight? boolean (default false). Decorative; hidden from a11y tree.
 */
export function Divider({ tight }: { tight?: boolean }) {
  return <hr className={`lk-divider${tight ? ' lk-divider--tight' : ''}`} aria-hidden="true" />
}
