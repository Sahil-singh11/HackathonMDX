/**
 * Shared island geometry — ONE source of truth for every surface that draws Mauritius.
 *
 * Before this module there were two independent coastlines: COAST_DEG in
 * components/onboarding/terrain.ts (welcome scene + tourism chart) and
 * public/geo/mauritius.geojson (Natural Earth, transport map). Two traces of the
 * same island drift apart the moment either is edited, and a marker plotted
 * against the wrong one sits in the sea.
 *
 * These 66 degree pairs are the traced outline that already backed the welcome
 * scene, closed into a valid GeoJSON ring. Named headlands are real and
 * identifiable: Cap Malheureux in the north, Le Morne in the south-west, the
 * Mahebourg notch in the south-east.
 *
 * WHAT IS NOT HERE, deliberately:
 *   - No fringing reef. This project has no reef dataset, and hand-drawing one
 *     would read as surveyed geography. It is the same rule that keeps the
 *     onboarding depth rings out of the tourism chart: never invent data you do
 *     not have. A licensed source (Allen Coral Atlas, UNEP-WCMC) would be needed
 *     first.
 *   - No bathymetry, roads, or place labels beyond markers a caller passes.
 *
 * Coordinates are [lon, lat], GeoJSON order — the OPPOSITE of Leaflet's
 * [lat, lng]. Use `toLatLngRing()` at the Leaflet boundary rather than
 * reordering by hand at each call site.
 */

/** Closed ring, GeoJSON [lon, lat] order. */
export const MAURITIUS_RING: Array<[number, number]> = [
  [57.614, -19.983], // Cap Malheureux
  [57.630, -19.990],
  [57.646, -19.997],
  [57.668, -20.012],
  [57.686, -20.037],
  [57.700, -20.066],
  [57.706, -20.093],
  [57.724, -20.111],
  [57.739, -20.128],
  [57.762, -20.156],
  [57.780, -20.192],
  [57.792, -20.214],
  [57.796, -20.238],
  [57.802, -20.262],
  [57.808, -20.290],
  [57.796, -20.318],
  [57.778, -20.348],
  [57.760, -20.378],
  [57.744, -20.404],
  [57.731, -20.428],
  [57.722, -20.440],
  [57.717, -20.449],
  [57.706, -20.442],
  [57.700, -20.428],
  [57.700, -20.407],
  [57.688, -20.417],
  [57.676, -20.432],
  [57.660, -20.448],
  [57.638, -20.462],
  [57.606, -20.481],
  [57.570, -20.502],
  [57.540, -20.514],
  [57.518, -20.520],
  [57.486, -20.516],
  [57.452, -20.508],
  [57.420, -20.500],
  [57.396, -20.494],
  [57.370, -20.496],
  [57.350, -20.492],
  [57.336, -20.480],
  [57.322, -20.472],
  [57.307, -20.462],
  [57.311, -20.448],
  [57.326, -20.443],
  [57.340, -20.446],
  [57.352, -20.436],
  [57.360, -20.408],
  [57.366, -20.376],
  [57.366, -20.325],
  [57.363, -20.296],
  [57.363, -20.274],
  [57.374, -20.244],
  [57.390, -20.221],
  [57.402, -20.208],
  [57.428, -20.190],
  [57.462, -20.176],
  [57.490, -20.168],
  [57.500, -20.161],
  [57.512, -20.132],
  [57.520, -20.100],
  [57.526, -20.062],
  [57.548, -20.036],
  [57.568, -20.020],
  [57.580, -20.013],
  [57.598, -19.996],
  [57.614, -19.983],
]

/** Named headlands, for verifying the outline is the real island. */
export const LANDMARKS = {
  capMalheureux: [57.614, -19.983] as [number, number],
  leMorne: [57.307, -20.462] as [number, number],
  mahebourg: [57.710, -20.408] as [number, number],
  souillac: [57.520, -20.520] as [number, number],
}

/** The island as a GeoJSON Feature — what the Leaflet GeoJSON layer consumes. */
export const MAURITIUS_GEOJSON: GeoJSON.Feature<GeoJSON.Polygon> = {
  type: 'Feature',
  properties: {
    name: 'Mauritius (main island)',
    note: 'Traced outline. Not for navigation. No reef, no bathymetry.',
  },
  geometry: { type: 'Polygon', coordinates: [MAURITIUS_RING] },
}

/** [lon,lat] -> [lat,lng] for Leaflet APIs. */
export function toLatLngRing(ring: Array<[number, number]>): Array<[number, number]> {
  return ring.map(([lon, lat]) => [lat, lon])
}

/** [south, west, north, east] covering the island, for fitBounds. */
export const MAURITIUS_BBOX: [number, number, number, number] = (() => {
  const lons = MAURITIUS_RING.map((p) => p[0])
  const lats = MAURITIUS_RING.map((p) => p[1])
  return [Math.min(...lats), Math.min(...lons), Math.max(...lats), Math.max(...lons)]
})()
