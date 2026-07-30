/**
 * Port Louis approach map — now an adapter over the shared ChartMap.
 *
 * THE HONESTY CONSTRAINT IS UNCHANGED, and is why this file still exists rather
 * than calling ChartMap inline:
 *
 *   AIS GIVES US A DISTANCE, NOT A BEARING.
 *
 * A map makes it very tempting to scatter vessel pins around the port. That
 * would be inventing positions, which honesty rule 4 forbids. So the map draws
 * exactly what the data supports:
 *
 *   - the port, at its true published coordinate
 *   - true-radius range rings (the approach radius plus 5 nm steps)
 *   - each vessel at its TRUE RANGE along ONE bearing, drawn dashed so it reads
 *     as a construction line, with the caveat stated in HTML under the map
 *
 * WHAT THE MIGRATION DELETED. The hand-rolled geodesic-circle helper is gone:
 * Leaflet's L.circle takes a radius in METRES and draws a real circle, so the
 * rings cannot drift out of agreement with the scale bar. The manual
 * above/below label alternation is gone too — ChartMap's de-collision pass now
 * solves that for every map in the app instead of this file solving it once for
 * itself. ~120 lines of MapLibre layer plumbing became a props object.
 */
import ChartMap, { type MapLine, type MapMarker, type MapRing } from '../../components/map/LazyChartMap'
import { useT } from '../../i18n'
import type { ArrivalsBrief } from './types'

const NM_TO_M = 1852

/**
 * The schematic approach bearing: 315° (NW) out of Port Louis.
 *
 * Chosen because it is open water for the whole ring extent — Mauritius lies
 * south and east of the port, so a westerly or south-westerly line would run
 * along the coast and put the further arrivals on land. This is a PRESENTATION
 * axis, not a claim: the caveat below the map says so.
 */
const APPROACH_BEARING = 315

/** Destination point at `distanceNm` on a compass bearing, as [lat, lng]. */
function along(lat: number, lon: number, distanceNm: number, bearingDeg: number): [number, number] {
  const km = (distanceNm * NM_TO_M) / 1000
  const rad = (bearingDeg * Math.PI) / 180
  const dLat = (km * Math.cos(rad)) / 110.574
  const dLon = (km * Math.sin(rad)) / (111.32 * Math.cos((lat * Math.PI) / 180))
  return [lat + dLat, lon + dLon]
}

export default function ApproachMap({ brief }: { brief: ArrivalsBrief }) {
  const t = useT()
  const { port, congestion, expected_arrivals: arrivals } = brief
  const { latitude: lat, longitude: lon } = port

  const approach = congestion.approach_radius_nm
  const furthest = arrivals.reduce((m, a) => Math.max(m, a.distance_nm), 0)
  const maxRing = Math.max(15, Math.ceil(Math.max(approach, furthest) / 5) * 5)

  const rings: MapRing[] = [{ centre: [lat, lon], radiusMetres: approach * NM_TO_M }]
  for (let r = 5; r <= maxRing; r += 5) {
    if (Math.abs(r - approach) < 2.5) continue // the approach ring is already in
    rings.push({ centre: [lat, lon], radiusMetres: r * NM_TO_M })
  }

  const lines: MapLine[] = [{
    points: [[lat, lon], along(lat, lon, maxRing, APPROACH_BEARING)],
    dashed: true,
  }]

  const ordered = [...arrivals].sort((a, b) => a.distance_nm - b.distance_nm)

  const markers: MapMarker[] = [
    {
      id: 'port',
      position: [lat, lon],
      label: port.name,
      status: 'info',
      shape: 'circle',
      detail: t('transport.portDetail'),
    },
    ...ordered.map((v, i) => ({
      id: `vessel-${i}`,
      // TRUE range, schematic bearing.
      position: along(lat, lon, v.distance_nm, APPROACH_BEARING),
      // Range is the label, because range is what AIS actually gave us.
      label: `${v.distance_nm.toFixed(1)} nm`,
      status: 'caution' as const,
      shape: 'diamond' as const,
      detail: v.vessel_name ?? t('transport.vesselUnnamed'),
    })),
  ]

  // Frame the outermost ring so the whole approach is visible without zooming.
  const pad = maxRing * 1.2
  const [nLat, eLon] = along(lat, lon, pad, 45)
  const [sLat, wLon] = along(lat, lon, pad, 225)

  return (
    <>
      <ChartMap
        markers={markers}
        rings={rings}
        lines={lines}
        bounds={[sLat, wLon, nLat, eLon]}
        height={420}
        listLabel={t('transport.approachListLabel')}
      />
      <p className="lkmap__disclaimer">{t('transport.bearingCaveat')}</p>
    </>
  )
}
