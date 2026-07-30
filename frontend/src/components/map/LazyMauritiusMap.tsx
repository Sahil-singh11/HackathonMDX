/**
 * Code-split wrapper for MauritiusMap.
 *
 * WHY. maplibre-gl is ~1 MB minified (395 KB gzipped) — it tripled the main
 * bundle when imported statically. The fisher-facing screens (Home, Record a
 * catch, Catch log, Sea conditions) have no map on them, and those are the
 * screens that must load on a bad connection on a boat. Paying 395 KB there to
 * render a map on a shore-side pillar page is the wrong trade.
 *
 * So the map — and MapLibre with it — is fetched only when a surface that
 * actually shows one mounts. Everything else keeps the original bundle.
 *
 * Offline note: the chunk is precached by the service worker in a production
 * build like any other asset, so a second visit still works with no signal. The
 * FIRST visit to a map surface needs a connection, which is stated where it
 * matters rather than hidden — the pillar surfaces are shore-side tools, not the
 * on-boat capture flow.
 */
import { Suspense, lazy } from 'react'
import { Skeleton } from '../ui'

const MauritiusMap = lazy(() => import('./MauritiusMap'))

export type { MapLayerApi } from './MauritiusMap'

type MapProps = React.ComponentProps<typeof MauritiusMap>

export default function LazyMauritiusMap(props: MapProps) {
  return (
    <Suspense fallback={<Skeleton height={`${props.height ?? 420}px`} />}>
      <MauritiusMap {...props} />
    </Suspense>
  )
}
