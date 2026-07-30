/**
 * MauritiusMap — MapLibre GL, with NO tile server.
 *
 * WHY THERE ARE NO TILES. A normal MapLibre style points at a raster or vector
 * tile endpoint, which means a network round-trip per tile. This app's whole
 * premise is that it works with no signal, and CLAUDE.md forbids CDN assets for
 * exactly that reason — a tile fetch fails precisely when a fisher needs the
 * app. So the style here has ONE source: a 2.9 KB GeoJSON of Mauritius served
 * from our own /geo/ directory (Natural Earth, public domain). Real pan, zoom,
 * Mercator projection and MapLibre rendering; zero requests off-device.
 *
 * What that costs, stated plainly: no satellite imagery, no place labels beyond
 * the ones we draw, no roads, no bathymetry. Land polygons and the sea. For a
 * marine app that is most of what matters, and it cannot go blank offline.
 *
 * Everything drawn ON the map comes from the caller via `layers` — this
 * component owns the basemap, the camera and the accessibility contract, and
 * knows nothing about vessels or dive sites.
 *
 * ACCESSIBILITY. The canvas is decoration: `role="presentation"`, removed from
 * the tab order, and every datum drawn on it must also exist in the caller's DOM
 * (a table or a button list). Under prefers-reduced-motion all camera movement
 * is instant rather than eased. In the Sunlight theme the map is not rendered at
 * all, matching every other canvas surface in the app.
 */
import { useEffect, useRef, useState } from 'react'
// maplibre-gl v6 removed the default export — named imports only. Marker is
// imported HERE, statically, alongside Map — this file is the one place that
// pays for the whole library, by design (see LazyMauritiusMap.tsx). An earlier
// version instead did `await import('maplibre-gl')` a second time inside the
// 'load' handler just to reach Marker, which produced a SECOND module instance
// under Vite's dep pre-bundling: the statically-imported Map created its
// worker/actor dispatcher against one module instance, while code running
// through the dynamic import path looked for it on another, so every actor
// message failed with "No actors found" — six uncaught exceptions per mount,
// and the GeoJSON source never finished loading because its worker reply had
// nowhere to land. One import path, and the errors and the blank map both
// disappeared in the same fix.
import { Map as MlMap, Marker, NavigationControl, ScaleControl, setWorkerUrl, type StyleSpecification } from 'maplibre-gl'

// SELF-HOSTED WORKER SCRIPT — the actual fix, not a workaround.
//
// With no explicit workerUrl, MapLibre derives its worker's location from its
// own module's URL at runtime. Under Vite's dev server AND the production
// build alike, once MapLibre is lazy-loaded into its own chunk (see
// LazyMauritiusMap.tsx), that derivation resolves to a URL the worker script
// is not actually served from: the Worker silently never comes up, its
// Dispatcher's actor promise never settles, and 'load' never fires — no
// thrown error, no console line, just a permanently blank map with a working
// background layer (which needs no source data) and nothing else. Verified in
// both `npm run dev` and `npm run build`, so this is not a dev-only artifact.
//
// A tried first-pass fix, setWorkerCount(0) (main-thread parsing, no worker at
// all), traded that hang for a different failure: GeoJSON tiling in this
// MapLibre version happens ONLY inside the worker, so with zero workers every
// fill/line layer silently rendered nothing — markers positioned correctly
// (they only need the camera, not the tile pipeline) while the coastline,
// range rings and approach circle simply never painted. Markers-only was not
// an acceptable trade.
//
// The real fix: point MapLibre at its OWN worker script, copied into
// public/vendor/ at the version pinned in package.json (BSD-3-Clause,
// redistributable — LICENSE.txt sits next to it). This is the same
// self-hosting pattern the app already uses for fonts, for the same reason:
// no CDN, no runtime URL guessing, works with the device offline.
setWorkerUrl('/vendor/maplibre-gl-worker.mjs')
import { useTheme } from '../../theme'
import 'maplibre-gl/dist/maplibre-gl.css'
import './map.css'

/** Main island only; Rodrigues and Agalega are ~600 km away and would collapse
 *  the useful zoom range if the initial camera had to contain them. */
export const MAIN_ISLAND_BOUNDS: [[number, number], [number, number]] = [
  [57.26, -20.56], [57.84, -19.94],
]

const GEOJSON_URL = '/geo/mauritius.geojson'

/** One paint set per theme, from the semantic tokens resolved at build time of
 *  the style (MapLibre needs literal colours, not CSS variables). */
function readPaint() {
  const cs = getComputedStyle(document.documentElement)
  const v = (name: string, fallback: string) => cs.getPropertyValue(name).trim() || fallback
  return {
    sea: v('--surface-sunken', '#DCE8EA'),
    land: v('--bg-alt', '#F5EFE6'),
    coast: v('--border-strong', '#5F7B82'),
  }
}

function buildStyle(): StyleSpecification {
  const p = readPaint()
  return {
    version: 8,
    // No glyphs/sprite URL: both would be network fetches. Any text we need is
    // drawn as an HTML marker instead, which also makes it translatable.
    sources: {
      mauritius: { type: 'geojson', data: GEOJSON_URL },
    },
    layers: [
      { id: 'sea', type: 'background', paint: { 'background-color': p.sea } },
      { id: 'land', type: 'fill', source: 'mauritius', paint: { 'fill-color': p.land } },
      {
        id: 'coast', type: 'line', source: 'mauritius',
        paint: { 'line-color': p.coast, 'line-width': 1.4 },
      },
    ],
  }
}

export interface MapLayerApi {
  map: MlMap
  /** True when the user has asked for reduced motion — skip easing. */
  reduceMotion: boolean
  /**
   * Adds an HTML marker.
   *
   * Callers get this instead of importing `Marker` themselves, and that is the
   * whole point: a static `import { Marker } from 'maplibre-gl'` in a caller
   * pulls the entire 1 MB library back into the main bundle and defeats the
   * lazy split (measured — the split produced a 2 KB chunk and left MapLibre in
   * the main one until this helper existed). Everything MapLibre stays inside
   * this module.
   */
  addMarker: (element: HTMLElement, lngLat: [number, number]) => void
  /** Fit the camera to a bounding box, respecting reduced motion. */
  fit: (sw: [number, number], ne: [number, number], padding?: number) => void
}

interface Props {
  /** Runs once the basemap is loaded; add sources/layers/markers here.
   *  Return a cleanup function to remove whatever it added. */
  layers?: (api: MapLayerApi) => void | (() => void)
  /** Initial camera. Defaults to the main island. */
  bounds?: [[number, number], [number, number]]
  /** Accessible name for the map region (the map itself is presentational,
   *  but the wrapper is labelled so the region is announced meaningfully). */
  label: string
  /** Rendered instead of the map in the Sunlight theme. */
  sunlightFallback?: React.ReactNode
  height?: number
}

export default function MauritiusMap({
  layers, bounds = MAIN_ISLAND_BOUNDS, label, sunlightFallback, height = 420,
}: Props) {
  const holder = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MlMap | null>(null)
  const { theme, reduceMotion } = useTheme()
  const [failed, setFailed] = useState<string | null>(null)

  useEffect(() => {
    if (theme === 'sunlight') return
    const el = holder.current
    if (!el) return

    // GUARDS THE STRICTMODE DOUBLE-INVOKE RACE. In dev, React.StrictMode mounts
    // an effect, cleans it up, then mounts it again — synchronously, before this
    // first map's 'load' event (which waits on the GeoJSON fetch) has resolved.
    // Without this flag the first mount's 'load' handler could still fire after
    // its own map.remove() had already run (StrictMode's cleanup can land before
    // the GeoJSON fetch that gates 'load' resolves), calling addSource/addLayer/
    // addMarker on a destroyed map. MapLibre accepted those calls without
    // throwing — no console error, no 'error' event, canvas present and WebGL
    // active, but a permanently blank basemap. `disposed` makes the stale
    // instance's handler a no-op instead of a silent write into the void.
    let disposed = false
    let cleanupLayers: (() => void) | void
    let map: MlMap
    try {
      map = new MlMap({
        container: el,
        style: buildStyle(),
        bounds,
        fitBoundsOptions: { padding: 24 },
        attributionControl: false,
        // Nothing to fetch beyond our own GeoJSON, so no need to keep a
        // tile-cache budget or a worker pool larger than one.
        maxZoom: 12,
        minZoom: 7,
        dragRotate: false,
        pitchWithRotate: false,
        touchZoomRotate: true,
      })
    } catch (err) {
      // WebGL can be unavailable (old device, blocked context, some VMs). The
      // caller always renders the same data in the DOM, so this degrades to a
      // stated absence rather than a blank hole.
      setFailed(err instanceof Error ? err.message : 'map unavailable')
      return
    }
    mapRef.current = map


    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ maxWidth: 110, unit: 'metric' }), 'bottom-left')

    // The canvas carries no information the DOM does not — keep it out of the
    // tab order and out of the accessibility tree.
    const canvas = map.getCanvas()
    canvas.setAttribute('role', 'presentation')
    canvas.setAttribute('tabindex', '-1')
    canvas.setAttribute('aria-hidden', 'true')

    map.on('error', (e) => {
      // A failed GeoJSON load is worth surfacing: the basemap would be an empty
      // blue rectangle and silently pretending otherwise would be worse.
      if (String(e?.error?.message || '').includes(GEOJSON_URL)) {
        setFailed('coastline data could not be loaded')
      }
    })

    map.on('load', () => {
      // Still guarded: StrictMode's double-invoke fires this effect, tears the
      // first mount down, then fires it again, all before the FIRST map's
      // 'load' — which waits on the GeoJSON fetch — has resolved. Without this
      // check the stale instance's callback still ran, adding sources/markers
      // to an already-removed map. MapLibre accepted those calls without
      // throwing, so it cost a permanently blank basemap with nothing in the
      // console to point at.
      if (disposed) return

      const markers: InstanceType<typeof Marker>[] = []
      const api: MapLayerApi = {
        map,
        reduceMotion,
        addMarker: (element, lngLat) => {
          markers.push(new Marker({ element }).setLngLat(lngLat).addTo(map))
        },
        fit: (sw, ne, padding = 28) => {
          map.fitBounds([sw, ne], { padding, duration: reduceMotion ? 0 : 900 })
        },
      }

      let cleanup: void | (() => void)
      try {
        cleanup = layers?.(api)
      } catch (err) {
        // A throw here previously failed silently: no 'error' event, no
        // pageerror, just a permanently blank basemap. Surfacing it costs
        // nothing and would have cut the debugging time above from an hour to
        // a console line.
        // eslint-disable-next-line no-console
        console.error('[MauritiusMap] layers() threw:', err)
      }
      cleanupLayers = () => {
        markers.forEach((m) => m.remove())
        if (typeof cleanup === 'function') cleanup()
      }
    })

    return () => {
      disposed = true
      if (typeof cleanupLayers === 'function') cleanupLayers()
      map.remove()
      mapRef.current = null
    }
    // theme is a dependency because the basemap colours are baked into the style.
  }, [theme, reduceMotion, layers, bounds])

  // Sunlight renders no canvas anywhere in this app: glare destroys soft edges,
  // and the caller's table already carries every figure.
  if (theme === 'sunlight') return <>{sunlightFallback ?? null}</>

  if (failed) {
    return (
      <p className="lk-map__failed" role="note">
        Map unavailable on this device ({failed}). Every position is listed below.
      </p>
    )
  }

  return (
    <div
      className="lk-map"
      style={{ height }}
      role="group"
      aria-label={label}
    >
      <div ref={holder} className="lk-map__canvas" />
    </div>
  )
}
