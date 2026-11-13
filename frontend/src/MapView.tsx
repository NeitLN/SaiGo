// Bản đồ Leaflet bọc trong một component (T56 R1): Leaflet dùng trực tiếp, không qua react-leaflet,
// để giữ logic vẽ đã kiểm trong layers.ts. Đây là chỗ duy nhất dùng phần tử DOM thường (R2).
import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { getNetwork, type AlgorithmResult, type LatLon } from './api'
import { MapLayers, readPalette } from './layers'

// Tâm quanh chợ Bến Thành (cùng tâm với data/config/areas.json).
const CENTER: L.LatLngTuple = [10.7725, 106.698]

export interface ExpandedNodes {
  dijkstra?: AlgorithmResult
  astar?: AlgorithmResult
}

export default function MapView({ onReady, onClick, expandedNodes }: {
  onReady: (layers: MapLayers) => void
  onClick: (p: LatLon) => void
  expandedNodes?: ExpandedNodes | null
}) {
  const el = useRef<HTMLDivElement>(null)
  const onClickRef = useRef(onClick)
  onClickRef.current = onClick
  const mapRef = useRef<L.Map | null>(null)
  const expandedLayerRef = useRef<L.LayerGroup | null>(null)
  const legendControlRef = useRef<L.Control | null>(null)

  useEffect(() => {
    const map = L.map(el.current!).setView(CENTER, 16)
    mapRef.current = map
    // Nền tile OSM chỉ để xem tương tác, không tải hàng loạt (docs/ARCHITECTURE.md mục 6).
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: 'Dữ liệu © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }).addTo(map)
    map.on('click', (e: L.LeafletMouseEvent) => onClickRef.current({ lat: e.latlng.lat, lon: e.latlng.lng }))

    // Pane riêng cho node đã mở rộng (A13): nằm dưới overlayPane (400) của tuyến đường, trên basemap (250).
    const pane = map.createPane('expanded-nodes')
    pane.style.zIndex = '350'
    pane.style.pointerEvents = 'none'

    const expLayer = L.layerGroup().addTo(map)
    expandedLayerRef.current = expLayer

    const layers = new MapLayers(map)
    onReady(layers)

    // T56 R8: mạng chặn tile OSM (vd. DNS không phân giải được) thì nền trống. Lỗi liên tiếp mà chưa tile nào
    // tải được → vẽ mạng đường từ dữ liệu đồ thị làm nền; vẫn giữ dòng ghi nguồn OSM.
    let loaded = 0
    let failed = 0
    let fallback = false
    tiles.on('tileload', () => { loaded += 1 })
    tiles.on('tileerror', () => {
      failed += 1
      if (fallback || loaded > 0 || failed < 3) return
      fallback = true
      getNetwork()
        .then((n) => {
          layers.setNetwork(n.lines)
          map.attributionControl.addAttribution('Không tải được nền OSM: đang vẽ mạng đường từ dữ liệu')
        })
        .catch(() => { fallback = false }) // backend chưa sẵn sàng: thử lại ở lần lỗi tile sau
    })
    // Khung bản đồ đổi kích thước theo bố cục: báo Leaflet tính lại để không bị ô trắng.
    const resize = new ResizeObserver(() => map.invalidateSize())
    resize.observe(el.current!)
    return () => {
      resize.disconnect()
      if (legendControlRef.current) {
        legendControlRef.current.remove()
        legendControlRef.current = null
      }
      map.remove()
      mapRef.current = null
      expandedLayerRef.current = null
    }
  }, [onReady])

  // Lớp vẽ node đã mở rộng và chú thích (T56 / A13)
  useEffect(() => {
    const map = mapRef.current
    const layer = expandedLayerRef.current
    if (!map || !layer) return

    layer.clearLayers()
    if (legendControlRef.current) {
      legendControlRef.current.remove()
      legendControlRef.current = null
    }

    if (!expandedNodes) return

    const d = expandedNodes.dijkstra
    const a = expandedNodes.astar
    const dTrace = d?.trace ?? []
    const aTrace = a?.trace ?? []

    if (dTrace.length === 0 && aTrace.length === 0) return

    const renderer = L.canvas({ pane: 'expanded-nodes' })
    // Cùng màu với tuyến (token Astryx đã đổi ra màu cụ thể cho canvas).
    const palette = readPalette(map.getContainer())

    // Dijkstra: chấm nhỏ màu xanh, nhạt (dưới tuyến)
    for (const [lon, lat] of dTrace) {
      L.circleMarker([lat, lon], {
        pane: 'expanded-nodes',
        renderer,
        radius: 3,
        color: palette.dijkstra,
        weight: 0.5,
        fillColor: palette.dijkstra,
        fillOpacity: 0.35,
        interactive: false,
      }).addTo(layer)
    }

    // A*: chấm nhỏ màu cam đậm hơn (vẽ sau để nổi trên các node trùng)
    for (const [lon, lat] of aTrace) {
      L.circleMarker([lat, lon], {
        pane: 'expanded-nodes',
        renderer,
        radius: 3.5,
        color: palette.astar,
        weight: 0.8,
        fillColor: palette.astar,
        fillOpacity: 0.85,
        interactive: false,
      }).addTo(layer)
    }

    // Chú thích nhỏ trên bản đồ: "Dijkstra mở N node · A* mở M node"; nếu trace_truncated thì "(hiện K đầu tiên)"
    const dText = d && d.expanded !== undefined
      ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-blue);opacity:0.6;margin-right:5px;vertical-align:middle;"></span>Dijkstra mở ${d.expanded} node${d.trace_truncated && d.trace ? ` (hiện ${d.trace.length} đầu tiên)` : ''}`
      : ''
    const aText = a && a.expanded !== undefined
      ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-orange);margin-right:5px;vertical-align:middle;"></span>A* mở ${a.expanded} node${a.trace_truncated && a.trace ? ` (hiện ${a.trace.length} đầu tiên)` : ''}`
      : ''
    const items = [dText, aText].filter(Boolean)

    if (items.length > 0) {
      const legend = new L.Control({ position: 'bottomleft' })
      legend.onAdd = () => {
        const div = L.DomUtil.create('div', 'expanded-legend')
        div.style.background = 'var(--color-background-card, rgba(255, 255, 255, 0.94))'
        div.style.color = 'var(--color-text-primary)'
        div.style.padding = '5px 10px'
        div.style.borderRadius = 'var(--radius-element, 6px)'
        div.style.fontSize = '12px'
        div.style.fontWeight = '500'
        div.style.boxShadow = '0 1px 4px rgba(0, 0, 0, 0.18)'
        div.style.border = '1px solid var(--color-border, rgba(0, 0, 0, 0.12))'
        div.style.pointerEvents = 'none'
        div.style.lineHeight = '1.4'
        div.innerHTML = items.join(' <span style="color: var(--color-text-secondary);">·</span> ')
        return div
      }
      legend.addTo(map)
      legendControlRef.current = legend
    }
  }, [expandedNodes])

  return <div ref={el} className="map-frame" />
}
