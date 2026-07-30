/**
 * Port Louis approach map — MapLibre GL over the self-hosted coastline.
 *
 * Replaces the hand-rolled canvas chart. Same honesty constraint, unchanged:
 *
 *   AIS GIVES US A DISTANCE, NOT A BEARING.
 *
 * A real map makes it very tempting to drop vessel pins around the port. That
 * would be inventing positions, which honesty rule 4 forbids outright. So what
 * the map draws is exactly what the data supports:
 *
 *   - the port, at its true published coordinate
 *   - TRUE-RADIUS range circles (the approach radius, plus 5 nm steps), computed
 *     as real geodesic circles rather than screen-space ellipses, so the scale
 *     bar and the rings agree
 *   - each vessel at its TRUE RANGE along ONE clearly-labelled bearing line
 *
 * The gain over the old canvas is real: correct Mercator projection, pan/zoom,
 * a live scale bar, and the coastline at Natural Earth resolution instead of a
 * hand-traced outline. What it deliberately does NOT gain is fake positions.
 */
import { useCallback } from 'react'
import MauritiusMap, { type MapLayerApi } from '../../components/map/LazyMauritiusMap'
import type { ArrivalsBrief } from './types'

const NM_TO_KM = 1.852

/**
 * A geodesic circle as a GeoJSON polygon. Drawn as real geography rather than a
 * fixed pixel radius so it stays true under pan and zoom — a screen-space circle
 * would silently disagree with the scale bar the moment the user zoomed.
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

/** Destination point at `distanceNm` from (lon,lat) on a compass bearing. */
function along(lon: number, lat: number, distanceNm: number, bearingDeg: number): [number, number] {
  const km = distanceNm * NM_TO_KM
  const br = (bearingDeg * Math.PI) / 180
  const dLat = (km * Math.cos(br)) / 110.574
  const dLon = (km * Math.sin(br)) / (111.320 * Math.cos((lat * Math.PI) / 180))
  return [lon + dLon, lat + dLat]
}

/**
 * The schematic approach bearing: 315° (NW) out of Port Louis.
 *
 * Chosen because it is open water for the whole ring extent — Mauritius lies
 * south and east of the port, so a westerly or south-westerly line would run
 * along the coast and put the further arrivals on land. This is a PRESENTATION
 * axis, not a claim: the legend says so, in HTML, right under the map.
 */
const APPROACH_BEARING = 315

export default function ApproachMap({ brief }: { brief: ArrivalsBrief }) {
  const { port, congestion, expected_arrivals: arrivals } = brief

  const layers = useCallback(({ map, reduceMotion, addMarker, fit }: MapLayerApi) => {
    const { latitude: lat, longitude: lon } = port
    const approach = congestion.approach_radius_nm
    const furthest = arrivals.reduce((m, a) => Math.max(m, a.distance_nm), 0)
    const maxRing = Math.max(15, Math.ceil(Math.max(approach, furthest) / 5) * 5)

    const rings = []
    for (let r = 5; r <= maxRing; r += 5) {
      if (Math.abs(r - approach) < 2.5) continue   // the approach ring is drawn separately
      rings.push({
        type: 'Feature' as const, properties: { nm: r },
        geometry: { type: 'Polygon' as const, coordinates: [circle(lon, lat, r)] },
      })
    }

    map.addSource('rings', { type: 'geojson', data: { type: 'FeatureCollection', features: rings } })
    map.addLayer({
      id: 'rings-line', type: 'line', source: 'rings',
      paint: {
        'line-color': getComputedStyle(document.documentElement).getPropertyValue('--border-strong').trim() || '#5F7B82',
        'line-width': 1, 'line-dasharray': [2, 3], 'line-opacity': 0.55,
      },
    })

    // The approach radius is the one ring that means something operationally
    // (congestion is counted inside it), so it gets the accent and a solid line.
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#0E7C86'
    map.addSource('approach', {
      type: 'geojson',
      data: {
        type: 'Feature', properties: {},
        geometry: { type: 'Polygon', coordinates: [circle(lon, lat, approach)] },
      },
    })
    map.addLayer({
      id: 'approach-fill', type: 'fill', source: 'approach',
      paint: { 'fill-color': accent, 'fill-opacity': 0.07 },
    })
    map.addLayer({
      id: 'approach-line', type: 'line', source: 'approach',
      paint: { 'line-color': accent, 'line-width': 2 },
    })

    // The bearing line the vessels sit on. Dotted, so it reads as a construction
    // line rather than a surveyed track.
    const end = along(lon, lat, maxRing, APPROACH_BEARING)
    map.addSource('axis', {
      type: 'geojson',
      data: {
        type: 'Feature', properties: {},
        geometry: { type: 'LineString', coordinates: [[lon, lat], end] },
      },
    })
    map.addLayer({
      id: 'axis-line', type: 'line', source: 'axis',
      paint: {
        'line-color': getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#4C6076',
        'line-width': 1, 'line-dasharray': [1, 3], 'line-opacity': 0.8,
      },
    })

    // Port marker.
    const portEl = document.createElement('div')
    portEl.className = 'lk-mk'
    portEl.innerHTML =
      `<span class="lk-mk__dot" style="background:${accent}"></span>` +
      `<span class="lk-mk__label">${port.name}</span>`
    addMarker(portEl, [lon, lat])

    // Vessels, nearest first, at TRUE range along the labelled bearing.
    const ink = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#0A2540'
    ;[...arrivals]
      .sort((a, b) => a.distance_nm - b.distance_nm)
      .forEach((v, i) => {
        const [vlon, vlat] = along(lon, lat, v.distance_nm, APPROACH_BEARING)
        const el = document.createElement('div')
        el.className = 'lk-mk' + (reduceMotion ? '' : ' lk-mk--animate')
        if (!reduceMotion) el.style.animationDelay = `${120 + i * 70}ms`
        // Range only — the name lives in the table, and five names inside 11 nm
        // collide at every zoom that fits the island.
        //
        // Labels ALTERNATE side. Arrivals cluster: 2.4 and 3.5 nm are ~1 nm
        // apart, so with every label below its dot the closer pairs overlapped
        // and partly hid each other (measured on the Night crop: "6.4 nm" and
        // "2.4 nm" were both half-covered). Odd-indexed labels flip above.
        el.classList.add(i % 2 === 0 ? 'lk-mk--below' : 'lk-mk--above')
        el.innerHTML =
          `<span class="lk-mk__dot" style="background:transparent;border-color:${ink}"></span>` +
          `<span class="lk-mk__label">${v.distance_nm.toFixed(1)} nm</span>`
        addMarker(el, [vlon, vlat])
      })

    // Frame the outermost ring so the whole approach is visible without the user
    // having to zoom out first.
    const sw = along(lon, lat, maxRing * 1.15, 225)
    const ne = along(lon, lat, maxRing * 1.15, 45)
    fit(sw, ne)
  }, [port, congestion, arrivals])

  return (
    <MauritiusMap
      label={`Approach map for ${port.name}`}
      layers={layers}
      height={420}
    />
  )
}
