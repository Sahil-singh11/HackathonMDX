/* Tourism site map — a thin adapter over the shared ChartMap.
 *
 * All this does is translate the pillar's vocabulary (suitability bands) into
 * the app-wide marker vocabulary. Everything else — projection, coastline,
 * scale bar, north arrow, badge de-collision, tooltips, the keyboard list,
 * theme handling — belongs to components/map and is identical on every map in
 * the app. That is the point of the consolidation: this file is 40 lines
 * instead of the 400-line bespoke canvas it replaces.
 */
import ChartMap, { type MapMarker } from '../../components/map/LazyChartMap'
import type { MarkerStatus } from '../../components/map/markers'
import { useT } from '../../i18n'
import type { Band } from './chartGeometry'

export interface ChartSite {
  site_id: string
  name: string
  latitude: number
  longitude: number
  protected_area: boolean
  band: Band
  rank: number | null
}

/** Suitability band -> shared status vocabulary (which fixes the shape). */
const BAND_STATUS: Record<Band, MarkerStatus> = {
  good: 'good',
  fair: 'caution',
  poor: 'poor',
  unknown: 'info',
}

interface Props {
  sites: ChartSite[]
  selectedId: string | null
  onSelect: (siteId: string) => void
}

export default function TourismMap({ sites, selectedId, onSelect }: Props) {
  const t = useT()

  // Ranked order when a ranking exists, so badge numbers match the cards below.
  const ordered = [...sites].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99))

  const markers: MapMarker[] = ordered.map((s) => ({
    id: s.site_id,
    position: [s.latitude, s.longitude],
    label: s.name,
    status: BAND_STATUS[s.band] ?? 'info',
    detail: [
      t(`tourism.rating.${s.band}`),
      s.protected_area ? t('tourism.protectedShort') : null,
    ].filter(Boolean).join(' · '),
  }))

  return (
    <ChartMap
      markers={markers}
      selectedId={selectedId}
      onSelect={onSelect}
      height={420}
      listLabel={t('tourism.siteListLabel')}
    />
  )
}
