/**
 * Code-split wrapper for ChartMap. Import THIS, not ChartMap directly.
 *
 * WHY. Leaflet is ~150 KB raw / ~43 KB gzipped. That is far lighter than the
 * MapLibre setup it replaced, but it is still weight the fisher-facing screens
 * (Home, Record a catch, Catch log, Sea conditions) would pay for without ever
 * showing a map — and those are exactly the screens that must load on a bad
 * connection on a boat.
 *
 * Measured on this branch: importing ChartMap statically put Leaflet in the main
 * bundle and pushed it from 139.5 KB to 182.1 KB gzipped. Splitting it here
 * returns the main bundle to its pre-map size and moves Leaflet into a chunk
 * fetched only when a surface that actually shows a map mounts.
 *
 * Offline note: the chunk is precached by the service worker in a production
 * build like any other asset, so a second visit works with no signal. The FIRST
 * visit to a map surface needs a connection — acceptable because the map
 * surfaces are shore-side pillar tools, not the on-boat capture flow, which has
 * no map at all.
 */
import { Suspense, lazy } from 'react'
import { Skeleton } from '../ui'

const ChartMap = lazy(() => import('./ChartMap'))

export type { ChartMapProps, MapLine, MapMarker, MapRing } from './ChartMap'

type Props = React.ComponentProps<typeof ChartMap>

export default function LazyChartMap(props: Props) {
  return (
    <Suspense fallback={<Skeleton height={`${props.height ?? 420}px`} />}>
      <ChartMap {...props} />
    </Suspense>
  )
}
