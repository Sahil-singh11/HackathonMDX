/**
 * Port Louis approach map — an adapter over the shared ChartMap.
 *
 * MERGE RESOLUTION, and worth reading before changing either half.
 *
 * Two changes landed on this file in parallel and both are kept:
 *
 *   1. THE MAP LIBRARY IS THE SHARED ONE. MapLibre is gone from the app; there is
 *      one Leaflet ChartMap now, and it is better for this file specifically:
 *      L.circle takes a radius in METRES and draws a true circle, so the approach
 *      ring cannot drift out of agreement with the scale bar. The hand-rolled
 *      geodesic-polygon helper this file used to carry is deleted, and the marker
 *      de-collision and the accessible side list come free.
 *
 *   2. THE HONESTY POSITION IS THE LATER FINDING, AND IT WINS. The earlier version
 *      of this file plotted expected arrivals at true range along one schematic
 *      315 degree bearing, with a caveat. That display is NOT restored, because
 *      the vessels behind it are not real: terrestrial AIS needs a receiver within
 *      roughly 40 nm and none covers Mauritius, so the arrivals feed can only ever
 *      serve a committed synthetic capture. Drawing generated positions is what
 *      honesty rule 4 forbids, and a caveat under the map does not convert
 *      invented data into observed data.
 *
 *      This is also why the file still type-checks: TransportSurface now leads
 *      with the sea-state ApproachBrief, which has no vessel list at all.
 *
 * So every feature drawn here is either a true position or a true distance:
 *
 *   - the port, at its published coordinate
 *   - the approach ring, true to scale
 *   - nothing else. Sea state has no position beyond the point it was sampled at,
 *     and nothing on this map pretends otherwise.
 *
 * If a real AIS feed for Mauritian waters is ever wired up, the vessel layer
 * belongs back here — as MapMarkers with real bearings, not along one axis.
 */
import ChartMap, { type MapMarker, type MapRing } from '../../components/map/LazyChartMap'
import { useT } from '../../i18n'
import type { ApproachBrief } from './types'

const NM_TO_M = 1852

/** The radius the transit assessment describes. Not from the payload: the
 *  approach brief carries no radius field, and inventing a smaller or larger one
 *  than the text implies would misstate the assessment's own scope. Kept in step
 *  with `transport.mapLegend`, which names the same figure on the page. */
const APPROACH_RADIUS_NM = 10

/** Destination point at `distanceNm` on a compass bearing, as [lat, lng].
 *  Used ONLY to frame the camera, never to place a feature. */
function along(lat: number, lon: number, distanceNm: number, bearingDeg: number): [number, number] {
  const km = (distanceNm * NM_TO_M) / 1000
  const rad = (bearingDeg * Math.PI) / 180
  const dLat = (km * Math.cos(rad)) / 110.574
  const dLon = (km * Math.sin(rad)) / (111.32 * Math.cos((lat * Math.PI) / 180))
  return [lat + dLat, lon + dLon]
}

export default function ApproachMap({ brief }: { brief: ApproachBrief }) {
  const t = useT()
  const { latitude: lat, longitude: lon, name } = brief.port

  const rings: MapRing[] = [
    { centre: [lat, lon], radiusMetres: APPROACH_RADIUS_NM * NM_TO_M },
  ]

  const markers: MapMarker[] = [{
    id: 'port',
    position: [lat, lon],
    label: name,
    status: 'info',
    shape: 'circle',
    detail: t('transport.portDetail'),
  }]

  // Frame a little outside the ring so the whole approach zone is visible
  // without the reader having to zoom out.
  const pad = APPROACH_RADIUS_NM * 1.6
  const [nLat, eLon] = along(lat, lon, pad, 45)
  const [sLat, wLon] = along(lat, lon, pad, 225)

  return (
    <ChartMap
      markers={markers}
      rings={rings}
      bounds={[sLat, wLon, nLat, eLon]}
      height={420}
      listLabel={t('transport.approachListLabel')}
    />
  )
}
