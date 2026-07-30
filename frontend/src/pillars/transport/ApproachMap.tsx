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
 *   - vessels ONLY when `arrivals` is passed, and only then (see below)
 *
 * THE OPTIONAL VESSEL LAYER. `arrivals` is opt-in, and the caller that passes it
 * is responsible for labelling the whole block as stand-in data — TransportSurface
 * renders a loud `synthetic` provenance badge above it. That is the arrangement
 * that lets this exist at all: the feed's own `data_kind` is `synthetic`, so it is
 * shown as a demonstration of the surface, never as observed traffic.
 *
 * Two constraints inside the layer itself:
 *
 *   AIS GIVES A DISTANCE, NOT A BEARING. Each vessel is drawn at its TRUE range
 *   along ONE schematic bearing, on a dashed construction line, so ranges can be
 *   read against the scale bar without implying a direction the data never had.
 *   315 degrees out of Port Louis is chosen because it is open water for the whole
 *   ring extent — a westerly or southerly axis would put the further arrivals on
 *   land, which would look like a plotting bug and read as a claim.
 *
 *   THE CAVEAT IS RENDERED IN HTML by the caller, under the map, never baked into
 *   the graphic where it cannot be translated or read aloud.
 */
import ChartMap, { type MapLine, type MapMarker, type MapRing } from '../../components/map/LazyChartMap'
import { useT } from '../../i18n'
import type { ApproachBrief, ArrivalsBrief } from './types'

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

/** Open water for the whole ring extent out of Port Louis. Presentation axis. */
const APPROACH_BEARING = 315

export default function ApproachMap({ brief, arrivals }: {
  brief: ApproachBrief
  /** Opt-in stand-in vessel layer. The caller must label it. */
  arrivals?: ArrivalsBrief
}) {
  const t = useT()
  const { latitude: lat, longitude: lon, name } = brief.port

  const vessels = arrivals?.expected_arrivals ?? []
  const furthest = vessels.reduce((m, v) => Math.max(m, v.distance_nm), 0)
  const outer = Math.max(APPROACH_RADIUS_NM, Math.ceil(furthest / 5) * 5)

  const rings: MapRing[] = [
    { centre: [lat, lon], radiusMetres: APPROACH_RADIUS_NM * NM_TO_M },
  ]
  // Extra 5 nm range rings only when there are vessels to read against them.
  for (let r = 5; r <= outer && vessels.length > 0; r += 5) {
    if (Math.abs(r - APPROACH_RADIUS_NM) < 2.5) continue
    rings.push({ centre: [lat, lon], radiusMetres: r * NM_TO_M })
  }

  // Dashed, so it reads as a construction line and not as a surveyed track.
  const lines: MapLine[] = vessels.length > 0
    ? [{ points: [[lat, lon], along(lat, lon, outer, APPROACH_BEARING)], dashed: true }]
    : []

  const markers: MapMarker[] = [
    {
      id: 'port',
      position: [lat, lon],
      label: name,
      status: 'info',
      shape: 'circle',
      detail: t('transport.portDetail'),
    },
    // Nearest first, so the side list reads in the order that matters.
    ...[...vessels].sort((a, b) => a.distance_nm - b.distance_nm).map((v, i) => ({
      id: `vessel-${v.mmsi ?? i}`,
      position: along(lat, lon, v.distance_nm, APPROACH_BEARING),
      // Range is the label because range is what AIS actually reports.
      label: `${v.distance_nm.toFixed(1)} nm`,
      status: 'caution' as const,
      shape: 'diamond' as const,
      detail: v.identity_known && v.vessel_name
        ? `${v.vessel_name} — ${v.nav_status}`
        : t('transport.vesselUnnamed'),
    })),
  ]

  // Frame a little outside the outermost ring so the whole zone is visible
  // without the reader having to zoom out.
  const pad = outer * 1.6
  const [nLat, eLon] = along(lat, lon, pad, 45)
  const [sLat, wLon] = along(lat, lon, pad, 225)

  return (
    <ChartMap
      markers={markers}
      rings={rings}
      lines={lines}
      bounds={[sLat, wLon, nLat, eLon]}
      /* The approach rings alone framed a pale fragment of the north-west coast
         with the island running off two edges. Framing the island too costs some
         ring zoom and tells the reader where Port Louis actually is. */
      includeIsland
      height={420}
      listLabel={t('transport.approachListLabel')}
    />
  )
}
