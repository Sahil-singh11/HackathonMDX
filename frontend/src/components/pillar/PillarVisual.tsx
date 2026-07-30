/* PillarVisual — the container slot for a chart or a map.
 *
 * Props
 *   children    ReactNode   the visual. Contents are NOT assumed (see below).
 *   title?      string      optional heading above the frame.
 *   caption?    ReactNode   one line under the frame. Put the claim the visual
 *                           must not overstate here, in HTML — not baked into
 *                           canvas pixels, where it cannot be translated or read
 *                           by a screen reader.
 *   aspect?     'wide' | 'square' | 'tall'   frame ratio. Default 'wide' (16/9).
 *   loading?    boolean     show the skeleton instead of children.
 *   empty?      boolean     show the empty state instead of children.
 *   emptyTitle? string      default 'Nothing to plot yet'.
 *   emptyBody?  ReactNode   why, and what to do about it.
 *   emptyAction? ReactNode  one next step.
 *
 * IT WILL RECEIVE A MapLibre COMPONENT, SO IT ASSUMES NOTHING ABOUT ITS CHILD.
 * No padding, no background, no colour applied to the child, and nothing reaching
 * into it. Two things it does guarantee, because a map needs both and a chart
 * does not care:
 *
 *   1. A REAL RESOLVED HEIGHT. MapLibre measures its container on init and
 *      renders nothing in a zero-height box. The frame sets its height from
 *      aspect-ratio and the inner layer is absolutely positioned to fill it, so
 *      the child always inherits a definite size rather than a percentage of
 *      auto.
 *   2. A STABLE BOX. The frame keeps its ratio across loading, empty and loaded,
 *      so the page does not jump when the visual arrives and a map does not have
 *      to re-measure after paint.
 *
 * VERIFIED WITH THE REAL MAP, not assumed. components/map/MauritiusMap takes
 * `height` as a NUMBER and applies it as an inline style, so it cannot be asked
 * to fill a parent and no stylesheet can outrank it — dropped in naively it sat
 * at 420px inside the frame. pillar.css overrides it (the one !important in this
 * module, commented there). Measured filling the frame with a painted canvas at
 * 1440px and 390px, in Day and Night. You do not need to pass a height; whatever
 * you pass is overruled.
 *
 * ONE THING TO KNOW WHEN YOU CONVERT: MauritiusMap renders NOTHING in Sunlight
 * (it returns its `sunlightFallback`), by its own design — glare destroys a
 * canvas. Pass that fallback, or pass `empty` in Sunlight, or the frame shows an
 * empty box in that theme.
 *
 * FIXED RATIO, THREE CHOICES, NOT A FREE NUMBER. An arbitrary ratio per page is
 * how six pages end up six different shapes, which is the problem this framework
 * exists to fix.
 *
 * THE EMPTY STATE IS REAL. Not the string "no data". Say what is absent and what
 * to do, the same as everywhere else in this app. `empty` is checked after
 * `loading`, so a slow load never flashes "nothing to plot".
 */
import type { ReactNode } from 'react'
import { EmptyState, Skeleton } from '../ui'

export function PillarVisual({
  children, title, caption, aspect = 'wide',
  loading = false, empty = false, emptyTitle = 'Nothing to plot yet', emptyBody, emptyAction,
}: {
  children?: ReactNode
  title?: string
  caption?: ReactNode
  aspect?: 'wide' | 'square' | 'tall'
  loading?: boolean
  empty?: boolean
  emptyTitle?: string
  emptyBody?: ReactNode
  emptyAction?: ReactNode
}) {
  let body: ReactNode
  if (loading) {
    /* Skeleton is aria-hidden by design, so the frame carries the live status
       for anyone not looking at it. */
    body = (
      <div className="lkp-visual__fill" role="status" aria-label="Loading">
        <Skeleton height="100%" />
      </div>
    )
  } else if (empty) {
    body = (
      <div className="lkp-visual__fill lkp-visual__fill--empty">
        <EmptyState title={emptyTitle} body={emptyBody} action={emptyAction} />
      </div>
    )
  } else {
    body = children
  }

  return (
    <section className="lkp-visual" aria-label={title ?? 'Visual'}>
      {title && <h2 className="lkp-visual__title">{title}</h2>}
      <div className={`lkp-visual__frame lkp-visual__frame--${aspect}`}>
        {body}
      </div>
      {caption && <p className="lkp-visual__caption">{caption}</p>}
    </section>
  )
}
