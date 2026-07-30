/**
 * Port Louis approach map — MapLibre GL over the self-hosted coastline.
 *
 * NOW FULLY HONEST BY CONSTRUCTION. The earlier version had to work around a
 * real problem: AIS gave a distance per vessel but no bearing, so vessels were
 * drawn along one schematic line with a legend admitting the direction was not
 * real. That whole compromise is gone, because the pillar no longer displays
 * synthetic vessels at all — every feature on this map is now a true position
 * or a true distance:
 *
 *   - the port, at its published coordinate
 *   - a TRUE GEODESIC circle at the approach radius the assessment refers to,
 *     computed as real geography rather than a fixed pixel radius, so it still
 *     agrees with the scale bar at any zoom
 *   - nothing else. Sea state has no position beyond the point it was sampled
 *     at, so nothing pretends otherwise.
 */
import { useCallback } from 'react'
import MauritiusMap, { type MapLayerApi } from '../../components/map/LazyMauritiusMap'
import type { ApproachBrief } from './types'

const NM_TO_KM = 1.852

/** The radius the transit assessment describes. Not from the payload: the
 *  approach brief carries no radius field, and inventing a smaller or larger
 *  one than the text implies would misstate the assessment's own scope. */
const APPROACH_RADIUS_NM = 10

/**
 * A geodesic circle as a GeoJSON polygon, so it stays true under pan and zoom.
 * A screen-space circle would silently disagree with the scale bar the moment
 * the user zoomed.
 */
function circle(lon: number, lat: number, radiusNm: number, steps = 96): number[][] {
  const km = radiusNm * NM_TO_KM
  const dLat = km / 110.574
  const dLon = km / (111.320 * Math.cos((lat * Math.PI) / 180))
  const ring: number[][] = []
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * Math.PI * 2
    ring.push([lon + dLon * Math.cos(a), lat + dLat * Math.sin(a)])
  }
  return ring
}

/** Destination point at `distanceNm` on a compass bearing — used only to frame
 *  the camera, never to place a feature. */
function along(lon: number, lat: number, distanceNm: number, bearingDeg: number): [number, number] {
  const km = distanceNm * NM_TO_KM
  const br = (bearingDeg * Math.PI) / 180
  const dLat = (km * Math.cos(br)) / 110.574
  const dLon = (km * Math.sin(br)) / (111.320 * Math.cos((lat * Math.PI) / 180))
  return [lon + dLon, lat + dLat]
}

const token = (name: string, fallback: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

export default function ApproachMap({ brief }: { brief: ApproachBrief }) {
  const { port } = brief

  const layers = useCallback(({ map, addMarker, fit }: MapLayerApi) => {
    const { latitude: lat, longitude: lon } = port
    const accent = token('--accent', '#0E7C86')

    // The approach zone the assessment applies to.
    map.addSource('approach', {
      type: 'geojson',
      data: {
        type: 'Feature', properties: {},
        geometry: { type: 'Polygon', coordinates: [circle(lon, lat, APPROACH_RADIUS_NM)] },
      },
    })
    map.addLayer({
      id: 'approach-fill', type: 'fill', source: 'approach',
      paint: { 'fill-color': accent, 'fill-opacity': 0.08 },
    })
    map.addLayer({
      id: 'approach-line', type: 'line', source: 'approach',
      paint: { 'line-color': accent, 'line-width': 2 },
    })

    // Port marker — a true position.
    const portEl = document.createElement('div')
    portEl.className = 'lk-mk'
    portEl.innerHTML =
      `<span class="lk-mk__dot" style="background:${accent}"></span>` +
      `<span class="lk-mk__label">${port.name}</span>`
    addMarker(portEl, [lon, lat])

    // Frame a little beyond the ring so the whole approach is visible without
    // the user having to zoom out first.
    fit(
      along(lon, lat, APPROACH_RADIUS_NM * 1.6, 225),
      along(lon, lat, APPROACH_RADIUS_NM * 1.6, 45),
    )
  }, [port])

  return (
    <MauritiusMap
      label={`Approach map for ${port.name}`}
      layers={layers}
      height={380}
    />
  )
}
