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
  alt?: AlgorithmResult
  bidijkstra?: AlgorithmResult
}

export interface ReplayProps {
  status: 'static' | 'playing' | 'paused' | 'reset' | 'ended'
  speed: number
  key: number
  onEnded: () => void
}

export default function MapView({ onReady, onClick, expandedNodes, replay }: {
  onReady: (layers: MapLayers) => void
  onClick: (p: LatLon) => void
  expandedNodes?: ExpandedNodes | null
  replay?: ReplayProps | null
}) {
  const el = useRef<HTMLDivElement>(null)
  const onClickRef = useRef(onClick)
  onClickRef.current = onClick
  const mapRef = useRef<L.Map | null>(null)
  const dLayerRef = useRef<L.LayerGroup | null>(null)
  const aLayerRef = useRef<L.LayerGroup | null>(null)
  const altLayerRef = useRef<L.LayerGroup | null>(null)
  const biLayerRef = useRef<L.LayerGroup | null>(null)
  // Một canvas cho mọi lần vẽ node mở rộng; tạo mới mỗi lần effect chạy sẽ để lại canvas cũ trên pane.
  const rendererRef = useRef<L.Canvas | null>(null)
  const legendControlRef = useRef<L.Control | null>(null)
  const legendDivRef = useRef<HTMLDivElement | null>(null)
  const currentStepRef = useRef<number>(0)
  const rafIdRef = useRef<number | null>(null)

  useEffect(() => {
    const map = L.map(el.current!).setView(CENTER, 16)
    mapRef.current = map
    // Nền tile OSM chỉ để xem tương tác, không tải hàng loạt (docs/ARCHITECTURE.md mục 6).
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: 'Dữ liệu © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }).addTo(map)
    map.on('click', (e: L.LeafletMouseEvent) => onClickRef.current({ lat: e.latlng.lat, lon: e.latlng.lng }))

    // Pane riêng cho node đã mở rộng (A13/A14): nằm dưới overlayPane (400) của tuyến đường, trên basemap (250).
    const pane = map.createPane('expanded-nodes')
    pane.style.zIndex = '350'
    pane.style.pointerEvents = 'none'

    // Bốn layer riêng cho Dijkstra, A*, ALT và Dijkstra hai chiều (vẽ theo thứ tự để các node nổi rõ)
    const dLayer = L.layerGroup().addTo(map)
    const aLayer = L.layerGroup().addTo(map)
    const altLayer = L.layerGroup().addTo(map)
    const biLayer = L.layerGroup().addTo(map)
    dLayerRef.current = dLayer
    aLayerRef.current = aLayer
    altLayerRef.current = altLayer
    biLayerRef.current = biLayer
    rendererRef.current = L.canvas({ pane: 'expanded-nodes' })

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
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = null
      }
      if (legendControlRef.current) {
        legendControlRef.current.remove()
        legendControlRef.current = null
        legendDivRef.current = null
      }
      map.remove()
      mapRef.current = null
      dLayerRef.current = null
      aLayerRef.current = null
      altLayerRef.current = null
      rendererRef.current = null
    }
  }, [onReady])

  // Lớp vẽ node đã mở rộng, phát lại animation và chú thích (T56 / A13, A14, A15, A17)
  useEffect(() => {
    const map = mapRef.current
    const dLayer = dLayerRef.current
    const aLayer = aLayerRef.current
    const altLayer = altLayerRef.current
    const biLayer = biLayerRef.current
    if (!map || !dLayer || !aLayer || !altLayer || !biLayer) return

    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current)
      rafIdRef.current = null
    }

    if (!expandedNodes) {
      dLayer.clearLayers()
      aLayer.clearLayers()
      altLayer.clearLayers()
      biLayer.clearLayers()
      if (legendControlRef.current) {
        legendControlRef.current.remove()
        legendControlRef.current = null
        legendDivRef.current = null
      }
      currentStepRef.current = 0
      return
    }

    const d = expandedNodes.dijkstra
    const a = expandedNodes.astar
    const alt = expandedNodes.alt
    const bi = expandedNodes.bidijkstra
    const dTrace = d?.trace ?? []
    const aTrace = a?.trace ?? []
    const altTrace = alt?.trace ?? []
    const biTrace = bi?.trace ?? []
    const totalSteps = Math.max(dTrace.length, aTrace.length, altTrace.length, biTrace.length)

    if (totalSteps === 0) {
      dLayer.clearLayers()
      aLayer.clearLayers()
      altLayer.clearLayers()
      biLayer.clearLayers()
      if (legendControlRef.current) {
        legendControlRef.current.remove()
        legendControlRef.current = null
        legendDivRef.current = null
      }
      currentStepRef.current = 0
      return
    }

    // Tạo chú thích nhỏ trên bản đồ nếu chưa có
    if (!legendControlRef.current) {
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
        legendDivRef.current = div
        return div
      }
      legend.addTo(map)
      legendControlRef.current = legend
    }

    const renderer = rendererRef.current ?? undefined
    const palette = readPalette(map.getContainer())

    const updateLegend = (step: number) => {
      const div = legendDivRef.current
      if (!div) return

      if (step >= totalSteps) {
        // Kết thúc: hiện đủ như lớp tĩnh của #112 / A15 / A17
        const dText = d && d.expanded !== undefined
          ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-blue);opacity:0.6;margin-right:5px;vertical-align:middle;"></span>Dijkstra mở ${d.expanded} node${d.trace_truncated && d.trace ? ` (hiện ${d.trace.length} đầu tiên)` : ''}`
          : ''
        const aText = a && a.expanded !== undefined
          ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-orange);margin-right:5px;vertical-align:middle;"></span>A* mở ${a.expanded} node${a.trace_truncated && a.trace ? ` (hiện ${a.trace.length} đầu tiên)` : ''}`
          : ''
        const altText = alt && alt.expanded !== undefined
          ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-teal);margin-right:5px;vertical-align:middle;"></span>ALT mở ${alt.expanded} node${alt.trace_truncated && alt.trace ? ` (hiện ${alt.trace.length} đầu tiên)` : ''}`
          : ''
        const biText = bi && bi.expanded !== undefined
          ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-pink);margin-right:5px;vertical-align:middle;"></span>Dijkstra hai chiều mở ${bi.expanded} node${bi.trace_truncated && bi.trace ? ` (hiện ${bi.trace.length} đầu tiên)` : ''}`
          : ''
        const items = [dText, aText, altText, biText].filter(Boolean)
        div.innerHTML = items.join(' <span style="color: var(--color-text-secondary);">·</span> ')
      } else {
        // Đang phát lại hoặc tạm dừng ở bước k
        const dCount = Math.min(step, dTrace.length)
        const aCount = Math.min(step, aTrace.length)
        const altCount = Math.min(step, altTrace.length)
        const biCount = Math.min(step, biTrace.length)
        const dTotal = d?.expanded ?? dTrace.length
        const aTotal = a?.expanded ?? aTrace.length
        const altTotal = alt?.expanded ?? altTrace.length
        const biTotal = bi?.expanded ?? biTrace.length

        const dText = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-blue);opacity:0.6;margin-right:5px;vertical-align:middle;"></span>Dijkstra ${dCount} / ${dTotal}`
        const aText = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-orange);margin-right:5px;vertical-align:middle;"></span>A* ${aCount} / ${aTotal}`
        const altText = alt
          ? ` <span style="color: var(--color-text-secondary);">·</span> <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-teal);margin-right:5px;vertical-align:middle;"></span>ALT ${altCount} / ${altTotal}`
          : ''
        const biText = bi
          ? ` <span style="color: var(--color-text-secondary);">·</span> <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-data-categorical-pink);margin-right:5px;vertical-align:middle;"></span>Dijkstra hai chiều ${biCount} / ${biTotal}`
          : ''

        div.innerHTML = `bước ${step}: ${dText} <span style="color: var(--color-text-secondary);">·</span> ${aText}${altText}${biText}`
      }
    }

    const renderRange = (fromStep: number, toStep: number) => {
      // Dijkstra: chấm nhỏ xanh nhạt (dưới tuyến)
      const dStart = Math.min(fromStep, dTrace.length)
      const dEnd = Math.min(toStep, dTrace.length)
      for (let i = dStart; i < dEnd; i++) {
        const [lon, lat] = dTrace[i]
        L.circleMarker([lat, lon], {
          pane: 'expanded-nodes',
          renderer,
          radius: 3,
          color: palette.dijkstra,
          weight: 0.5,
          fillColor: palette.dijkstra,
          fillOpacity: 0.35,
          interactive: false,
        }).addTo(dLayer)
      }

      // A*: chấm nhỏ cam đậm hơn (vẽ sau để nổi trên các node trùng)
      const aStart = Math.min(fromStep, aTrace.length)
      const aEnd = Math.min(toStep, aTrace.length)
      for (let i = aStart; i < aEnd; i++) {
        const [lon, lat] = aTrace[i]
        L.circleMarker([lat, lon], {
          pane: 'expanded-nodes',
          renderer,
          radius: 3.5,
          color: palette.astar,
          weight: 0.8,
          fillColor: palette.astar,
          fillOpacity: 0.85,
          interactive: false,
        }).addTo(aLayer)
      }

      // ALT: chấm nhỏ teal
      if (alt) {
        const altStart = Math.min(fromStep, altTrace.length)
        const altEnd = Math.min(toStep, altTrace.length)
        for (let i = altStart; i < altEnd; i++) {
          const [lon, lat] = altTrace[i]
          L.circleMarker([lat, lon], {
            pane: 'expanded-nodes',
            renderer,
            radius: 3.5,
            color: palette.alt,
            weight: 0.8,
            fillColor: palette.alt,
            fillOpacity: 0.85,
            interactive: false,
          }).addTo(altLayer)
        }
      }

      // Dijkstra hai chiều: chấm nhỏ pink (loang từ cả 2 đầu s và t)
      if (bi) {
        const biStart = Math.min(fromStep, biTrace.length)
        const biEnd = Math.min(toStep, biTrace.length)
        for (let i = biStart; i < biEnd; i++) {
          const [lon, lat] = biTrace[i]
          L.circleMarker([lat, lon], {
            pane: 'expanded-nodes',
            renderer,
            radius: 3.5,
            color: palette.bidijkstra,
            weight: 0.8,
            fillColor: palette.bidijkstra,
            fillOpacity: 0.85,
            interactive: false,
          }).addTo(biLayer)
        }
      }
    }

    const status = replay?.status ?? 'static'
    const speed = Math.max(1, replay?.speed ?? 5)

    if (status === 'reset') {
      dLayer.clearLayers()
      aLayer.clearLayers()
      altLayer.clearLayers()
      biLayer.clearLayers()
      currentStepRef.current = 0
      updateLegend(0)
    } else if (status === 'static' || status === 'ended') {
      dLayer.clearLayers()
      aLayer.clearLayers()
      altLayer.clearLayers()
      biLayer.clearLayers()
      renderRange(0, totalSteps)
      currentStepRef.current = totalSteps
      updateLegend(totalSteps)
    } else if (status === 'paused') {
      updateLegend(currentStepRef.current)
    } else if (status === 'playing') {
      if (currentStepRef.current >= totalSteps) {
        dLayer.clearLayers()
        aLayer.clearLayers()
        altLayer.clearLayers()
        biLayer.clearLayers()
        currentStepRef.current = 0
      }

      const animate = () => {
        const prev = currentStepRef.current
        const next = Math.min(prev + speed, totalSteps)
        renderRange(prev, next)
        currentStepRef.current = next
        updateLegend(next)

        if (next < totalSteps) {
          rafIdRef.current = requestAnimationFrame(animate)
        } else {
          rafIdRef.current = null
          replay?.onEnded()
        }
      }
      rafIdRef.current = requestAnimationFrame(animate)
    }

    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = null
      }
    }
  }, [expandedNodes, replay?.status, replay?.speed, replay?.key])

  return <div ref={el} className="map-frame" />
}
