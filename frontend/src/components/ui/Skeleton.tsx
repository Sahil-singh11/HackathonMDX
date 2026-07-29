/**
 * Skeleton — FROZEN. Loading placeholder; prefer this over a spinner for
 * page/section loads so layout does not jump when data arrives.
 * Props: width? / height? CSS lengths, text? boolean (line-shaped), count? number
 */
export function Skeleton({ width, height, text, count = 1 }: {
  width?: string; height?: string; text?: boolean; count?: number
}) {
  return (
    <span aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className={`lk-skeleton${text ? ' lk-skeleton--text' : ''}`}
          style={{ display: 'block', width: width ?? '100%', height: height ?? (text ? undefined : '1.5rem') }} />
      ))}
    </span>
  )
}
