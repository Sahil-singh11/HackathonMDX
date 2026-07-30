/**
 * ChartMap — the one map component for the whole app. Leaflet, NO TILE LAYER.
 *
 * WHY NO TILES. A tile layer is a network request per tile. This app's premise
 * is that it works with no signal, and CLAUDE.md forbids CDN assets for exactly
 * that reason: the fetch fails precisely when someone needs the app. So there is
 * no L.tileLayer here, no style URL, and nothing fetched at runtime. The
 * background is our own `--surface-sunken` token and every piece of geometry is
 * GeoJSON we ship in the bundle (components/map/geometry.ts).
 *
 * The CRS stays Leaflet's default EPSG3857. CRS.Simple would be tempting for a
 * "chart" look, but then real lat/lng stops meaning anything and markers drift
 * off the coast — the one thing a map must never do.
 *
 * WHAT IT COSTS, plainly: no imagery, no roads, no place names beyond the
 * markers a caller passes, no bathymetry, no reef. Land and sea. For a marine
 * app that is most of what matters, and it cannot go blank offline.
 *
 * ACCESSIBILITY — a map is never the only route. Every marker is also rendered
 * as a keyboard-navigable button in the side list, with the same label, status
 * and click action. The Leaflet pane itself is reachable but the list is the
 * supported path, and in the Sunlight theme (extreme-contrast, for direct sun on
 * a deck) the map is not drawn at all and the list stands alone.
 *
 * PROPS
 *   markers    MapMarker[]   coordinate, label, status, optional shape/badge
 *   rings      MapRing[]     approach radii, in metres
 *   bounds     [S,W,N,E]     or use centre/zoom
 *   centre     [lat,lng]
 *   zoom       number
 *   height     number        px
 *   onSelect   (id) => void
 *   selectedId string
 *   listLabel  string        accessible name for the side list
 */
import 'leaflet/dist/leaflet.css' // must be explicit; Leaflet ships unstyled otherwise
import L from 'leaflet'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useT } from '../../i18n'
import { COASTLINE_ATTRIBUTION, MAURITIUS_BBOX, MAURITIUS_GEOJSON } from './geometry'
import { buildMarkerIcon, decollide, northArrowHtml, type MarkerShape, type MarkerStatus } from './markers'
import './map.css'

export interface MapMarker {
  id: string
  /** True position, [lat, lng]. */
  position: [number, number]
  label: string
  status: MarkerStatus
  shape?: MarkerShape
  /** Secondary line in the side list; never drawn on the map. */
  detail?: string
}

export interface MapRing {
  centre: [number, number]
  radiusMetres: number
  label?: string
}

/**
 * A polyline in true coordinates — a bearing axis, an approach corridor, a
 * track. `dashed` is for construction lines that must not read as surveyed
 * geography (e.g. the single bearing AIS vessels are plotted along).
 */
export interface MapLine {
  points: Array<[number, number]>
  dashed?: boolean
}

export interface ChartMapProps {
  markers: MapMarker[]
  rings?: MapRing[]
  lines?: MapLine[]
  bounds?: [number, number, number, number]
  centre?: [number, number]
  zoom?: number
  height?: number
  selectedId?: string | null
  onSelect?: (id: string) => void
  listLabel?: string
}

function useTheme(): string {
  const [theme, setTheme] = useState(
    () => document.documentElement.getAttribute('data-theme') ?? 'day')
  useEffect(() => {
    const el = document.documentElement
    const obs = new MutationObserver(() =>
      setTheme(el.getAttribute('data-theme') ?? 'day'))
    obs.observe(el, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])
  return theme
}

export default function ChartMap({
  markers, rings = [], lines = [], bounds, centre, zoom, height = 420,
  selectedId = null, onSelect, listLabel,
}: ChartMapProps) {
  const t = useT()
  const theme = useTheme()
  const hostRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerRef = useRef<L.LayerGroup | null>(null)

  // Sunlight is deliberately map-free: hard contrast, no shadows, no canvas
  // surfaces. The list below carries everything the map would have shown.
  const drawMap = theme !== 'sunlight'

  const badged = useMemo(
    () => markers.map((m, i) => ({ ...m, badge: i + 1 })), [markers])

  // --- create the map once ------------------------------------------------
  useEffect(() => {
    if (!drawMap || !hostRef.current || mapRef.current) return

    const map = L.map(hostRef.current, {
      // Default CRS (EPSG3857) — real coordinates must plot correctly.
      // ON, and it must stay on: the coastline is OpenStreetMap data under
      // ODbL-1.0, which requires the credit to be shown wherever it is displayed.
      // There is still no tile layer here, so this control carries exactly one
      // line and it is the licence one.
      attributionControl: true,
      zoomControl: true,
      /* FRACTIONAL ZOOM, so fitBounds actually fits.
         Leaflet snaps to integer zoom by default, and an integer step is a factor
         of two — so a box that needs zoom 9.4 gets zoom 9 and the island lands at
         roughly half the size the frame could hold. That is what made this map
         read as a small diagram floating in empty space. zoomSnap: 0 lets the fit
         be exact; zoomDelta keeps the +/- buttons stepping a sensible amount. */
      zoomSnap: 0,
      zoomDelta: 0.5,
      // The page must still scroll on a phone; wheel zoom arms on focus/click.
      scrollWheelZoom: false,
      fadeAnimation: false,
      zoomAnimation: false,
      markerZoomAnimation: false,
    })
    mapRef.current = map

    L.geoJSON(MAURITIUS_GEOJSON, {
      style: { className: 'lkmap-land' },
      // The ODbL credit rides with the layer that carries the data, so it cannot
      // be separated from it by a later refactor.
      attribution: COASTLINE_ATTRIBUTION,
    }).addTo(map)

    L.control.scale({ metric: true, imperial: false, position: 'bottomleft' }).addTo(map)

    const North = L.Control.extend({
      onAdd() {
        const div = L.DomUtil.create('div', 'lkmap-north-control')
        div.innerHTML = northArrowHtml(t('map.north'))
        return div
      },
    })
    new North({ position: 'topright' }).addTo(map)

    layerRef.current = L.layerGroup().addTo(map)

    // Arm wheel zoom only once the user has engaged with the map.
    const enable = () => map.scrollWheelZoom.enable()
    const disable = () => map.scrollWheelZoom.disable()
    map.on('focus click', enable)
    map.on('blur mouseout', disable)

    return () => {
      map.off()
      map.remove()
      mapRef.current = null
      layerRef.current = null
    }
  }, [drawMap, t])

  // --- camera -------------------------------------------------------------
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const box = bounds ?? MAURITIUS_BBOX
    if (centre && zoom != null) map.setView(centre, zoom, { animate: false })
    else map.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: [24, 24], animate: false })
  }, [bounds, centre, zoom, drawMap])

  // --- markers and rings --------------------------------------------------
  useEffect(() => {
    const map = mapRef.current
    const group = layerRef.current
    if (!map || !group) return
    group.clearLayers()

    for (const line of lines) {
      L.polyline(line.points, {
        className: `lkmap-line${line.dashed ? ' lkmap-line--dashed' : ''}`,
        interactive: false,
      }).addTo(group)
    }

    for (const ring of rings) {
      L.circle(ring.centre, {
        radius: ring.radiusMetres,
        className: 'lkmap-ring',
        interactive: false,
      }).addTo(group)
    }

    // One de-collision pass in screen space, so badges stay readable without a
    // clustering plugin hiding markers behind a count.
    const projected = badged.map((m) => {
      const pt = map.latLngToContainerPoint(m.position)
      return { id: m.id, x: pt.x, y: pt.y }
    })
    const offsets = decollide(projected)

    for (const m of badged) {
      const icon = buildMarkerIcon({
        status: m.status, shape: m.shape, badge: m.badge,
        selected: m.id === selectedId,
      })
      const marker = L.marker(m.position, {
        icon,
        keyboard: true,
        title: m.label, // native tooltip fallback
        alt: m.label,
      })
      const off = offsets[m.id]
      if (off) {
        // Nudge the rendered icon only; the anchor stays on the true position.
        marker.setIcon(L.divIcon({
          ...(icon.options as L.DivIconOptions),
          className: 'lkmap-divicon lkmap-divicon--offset',
          iconAnchor: [14 - off[0], 14 - off[1]],
        }))
      }
      // Hover AND keyboard focus, never permanent — Leaflet cannot avoid label
      // collisions, so permanent tooltips overlap into noise.
      marker.bindTooltip(m.label, { direction: 'top', opacity: 1, className: 'lkmap-tooltip' })
      marker.on('click', () => onSelect?.(m.id))
      marker.on('keypress', (e) => {
        if ((e as unknown as KeyboardEvent).code === 'Enter') onSelect?.(m.id)
      })
      marker.addTo(group)
    }
  }, [badged, rings, lines, selectedId, onSelect, drawMap])

  return (
    <div className="lkmap">
      {drawMap ? (
        <div
          ref={hostRef}
          className="lkmap__canvas"
          style={{ height: `${height}px` }}
          role="application"
          aria-label={t('map.ariaLabel')}
        />
      ) : (
        <p className="lkmap__sunlight-note">{t('map.sunlightNote')}</p>
      )}

      {/* The non-map equivalent. Same markers, same order, same badge numbers,
          same action — and the only path in Sunlight. */}
      <ul className="lkmap__list" aria-label={listLabel ?? t('map.listLabel')}>
        {badged.map((m) => (
          <li key={m.id}>
            <button
              type="button"
              className={`lkmap__list-item${m.id === selectedId ? ' is-selected' : ''}`}
              aria-pressed={m.id === selectedId}
              onClick={() => onSelect?.(m.id)}
            >
              <span className={`lkmap__list-badge lkmap__list-badge--${m.status}`}>{m.badge}</span>
              <span className="lkmap__list-text">
                <span className="lkmap__list-label">{m.label}</span>
                {m.detail && <span className="lkmap__list-detail">{m.detail}</span>}
              </span>
              <span className="lkmap__list-status">{t(`map.status.${m.status}`)}</span>
            </button>
          </li>
        ))}
      </ul>

      <p className="lkmap__disclaimer">{t('map.disclaimer')}</p>
    </div>
  )
}
