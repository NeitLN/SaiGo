// Các lớp vẽ trên bản đồ Leaflet (docs/DEMO.md mục 1.2): vùng ùn tắc, điểm đi/đến, tuyến Dijkstra và A*,
// đoạn bị đóng (T54), kho và điểm giao của tour (T73).
import L from 'leaflet'
import type { AlgorithmResult, LatLon, RouteResponse, Scenario } from './api'

// Màu lấy từ token của theme Astryx (đọc trên phần tử bản đồ, nằm trong <Theme>), không viết mã màu cứng.
type Palette = {
  dijkstra: string; astar: string; source: string; target: string; closed: string; zone: string; tour: string; surface: string
  road: string
}

function readPalette(el: HTMLElement): Palette {
  // Token có thể là `light-dark(#.., #..)`: SVG/canvas không hiểu hàm này (canvas rơi về màu đen), nên đổi ra
  // màu cụ thể bằng cách gán vào `color` của một phần tử thử rồi đọc lại giá trị đã tính.
  const probe = document.createElement('i')
  el.appendChild(probe)
  const v = (name: string) => {
    probe.style.color = `var(${name})`
    return getComputedStyle(probe).color
  }
  const palette = {
    dijkstra: v('--color-data-categorical-blue'),
    astar: v('--color-data-categorical-orange'),
    source: v('--color-data-categorical-green'),
    target: v('--color-data-categorical-red'),
    closed: v('--color-error'),
    zone: v('--color-data-categorical-orange'),
    tour: v('--color-data-categorical-purple'),
    surface: v('--color-background-card'),
    road: v('--color-text-secondary'),
  }
  probe.remove()
  return palette
}

// GeoJSON là [lon, lat]; Leaflet cần [lat, lon].
export function toLatLngs(coords: [number, number][]): L.LatLng[] {
  return coords.map(([lon, lat]) => L.latLng(lat, lon))
}

function sameRoute(a?: AlgorithmResult, b?: AlgorithmResult): boolean {
  if (!a || !b || a.status !== 'ok' || b.status !== 'ok') return false
  if (a.edge_ids && b.edge_ids) return a.edge_ids.join(',') === b.edge_ids.join(',')
  return JSON.stringify(a.geometry.coordinates) === JSON.stringify(b.geometry.coordinates)
}

/** Một đoạn của tuyến (một cạnh có hướng) mà người dùng bấm để đóng (T54). */
export interface RouteSegment {
  edgeId: number
  twinId: number | null
  latlngs: L.LatLng[]
}

/** Phần chung của một tuyến hai điểm và một phương án tour: danh sách cạnh kèm hình học từng cạnh. */
interface EdgePath {
  status?: string
  edge_ids?: number[]
  edge_twin_ids?: (number | null)[]
  edge_geometries?: [number, number][][]
}

/** Tách tuyến thành từng cạnh theo `edge_geometries` (T54, #100): phần tử i là hình học của `edge_ids[i]`. */
export function routeSegments(r: EdgePath): RouteSegment[] {
  const ids = r.edge_ids ?? []
  const geoms = r.edge_geometries ?? []
  if ((r.status !== undefined && r.status !== 'ok') || geoms.length !== ids.length) return []
  return ids.map((edgeId, i) => ({ edgeId, twinId: r.edge_twin_ids?.[i] ?? null, latlngs: toLatLngs(geoms[i]) }))
}

export interface TourPoint extends LatLon {
  id: string
  label: string
}

export class MapLayers {
  private zones = L.layerGroup()
  private routes = L.layerGroup()
  private closed = L.layerGroup()
  private points = L.layerGroup()
  private network: L.Layer | null = null
  private palette: Palette
  private map: L.Map

  constructor(map: L.Map) {
    this.map = map
    this.palette = readPalette(map.getContainer())
    // Marker điểm đi/đến/kho nằm trong pane riêng, trên vùng bấm 18 px của tuyến (overlayPane, z 400) và dưới
    // marker điểm giao (markerPane, z 600). Nếu chung pane, vùng bấm vẽ sau sẽ đè lên marker: bấm vào marker
    // "Đi" lại đóng mất cạnh đầu tuyến (QA-8).
    map.createPane('points').style.zIndex = '450'
    this.zones.addTo(map)
    this.routes.addTo(map)
    this.closed.addTo(map)
    this.points.addTo(map)
  }

  /**
   * Nền dự phòng khi không tải được tile OSM (T56 R8): vẽ mạng đường của vùng demo từ dữ liệu đồ thị.
   * Pane riêng nằm trên lớp tile, dưới mọi lớp vẽ khác; canvas cho ~2.700 đường; không bấm được để
   * cú bấm vẫn rơi xuống bản đồ (chọn điểm).
   */
  setNetwork(lines: [number, number][][]) {
    if (this.network) this.network.remove()
    const pane = this.map.getPane('basemap') ?? this.map.createPane('basemap')
    pane.style.zIndex = '250'
    pane.style.pointerEvents = 'none'
    const renderer = L.canvas({ pane: 'basemap' })
    this.network = L.polyline(lines.map(toLatLngs), {
      pane: 'basemap', renderer, color: this.palette.road, weight: 1.5, opacity: 0.35, interactive: false,
    }).addTo(this.map)
  }

  // Vùng ùn tắc của kịch bản: hình tròn tô nhạt, không bấm được để không chặn thao tác chọn điểm.
  setZones(scenario: Scenario) {
    this.zones.clearLayers()
    for (const rule of scenario.rules) {
      const z = rule.zone
      if (z.type !== 'circle') continue // chỉ biết vẽ vùng tròn (CongestionZone)
      // Gộp primary/primary_link thành một tên cho nhãn ngắn (luật vẫn áp đúng danh sách gốc).
      const kinds = [...new Set((rule.highway ?? []).map((h) => h.replace(/_link$/, '')))]
      const roads = kinds.length ? ` · ${kinds.join(', ')}` : ''
      L.circle([z.lat, z.lon], {
        radius: z.radius_m, color: this.palette.zone, weight: 1, fillColor: this.palette.zone, fillOpacity: 0.15, interactive: false,
      }).addTo(this.zones)
      L.tooltip({ permanent: true, direction: 'center', className: 'zone-label', interactive: false })
        .setLatLng([z.lat, z.lon])
        .setContent(`Cao điểm mô phỏng · ×${rule.alpha.toLocaleString('vi-VN')}${roads}`)
        .addTo(this.zones)
    }
  }

  private marker(p: LatLon, label: string, color: string, tooltip?: string) {
    // Bấm vào marker không lan xuống bản đồ (không chọn lại điểm, không đóng đoạn). Leaflet chỉ dừng lan sự kiện
    // ở layer có nghe 'click', nên cần cả listener rỗng lẫn bubblingMouseEvents: false.
    return L.circleMarker([p.lat, p.lon], {
      radius: 7, color, weight: 3, fillColor: this.palette.surface, fillOpacity: 1, pane: 'points', bubblingMouseEvents: false,
    })
      .on('click', () => {})
      .bindTooltip(tooltip ? `${label} · ${tooltip}` : label, { permanent: true, direction: 'top', offset: [0, -6] })
      .addTo(this.points)
  }

  // Điểm người dùng bấm, trước khi có kết quả.
  setPoints(source: LatLon | null, target: LatLon | null) {
    this.points.clearLayers()
    if (source) this.marker(source, 'Đi', this.palette.source)
    if (target) this.marker(target, 'Đến', this.palette.target)
  }

  // Sau khi có kết quả: marker đặt tại node đã snap, tooltip ghi khoảng cách snap.
  setSnapped(res: RouteResponse) {
    this.points.clearLayers()
    const { source: s, target: t } = res.snapped
    this.marker(s, 'Đi', this.palette.source, `cách ${s.snap_distance_m.toFixed(0)} m`)
    this.marker(t, 'Đến', this.palette.target, `cách ${t.snap_distance_m.toFixed(0)} m`)
  }

  /**
   * Vẽ tuyến Dijkstra và A* (trùng nhau thì một nét có viền, ARCHITECTURE mục 6). Khi có `onSegmentClick`,
   * mỗi cạnh của tuyến Dijkstra có một nét trong suốt rộng để bấm đóng đoạn (T54).
   */
  drawRoutes(res: RouteResponse, onSegmentClick?: (seg: RouteSegment) => void) {
    this.routes.clearLayers()
    const d = res.results.dijkstra
    const a = res.results.astar
    if (sameRoute(d, a)) {
      const latlngs = toLatLngs(d!.geometry.coordinates)
      L.polyline(latlngs, { color: this.palette.astar, weight: 10, opacity: 0.9, interactive: false }).addTo(this.routes)
      L.polyline(latlngs, { color: this.palette.dijkstra, weight: 5, interactive: false }).addTo(this.routes)
    } else {
      if (d?.status === 'ok') {
        L.polyline(toLatLngs(d.geometry.coordinates), { color: this.palette.dijkstra, weight: 6, opacity: 0.8, interactive: false })
          .addTo(this.routes)
      }
      if (a?.status === 'ok') {
        L.polyline(toLatLngs(a.geometry.coordinates), { color: this.palette.astar, weight: 4, dashArray: '8 6', interactive: false })
          .addTo(this.routes)
      }
    }
    if (onSegmentClick && d) this.addHitSegments(routeSegments(d), onSegmentClick)
  }

  /**
   * Vùng bấm để đóng đoạn trên tuyến hoặc tour (T54, R1). Cạnh ngắn chỉ dài vài pixel nên vùng bấm 18 px
   * của các cạnh kề nhau chồng lên nhau, và nét vẽ sau sẽ "ăn" cú bấm. Vì vậy không tin nét nào nằm trên:
   * khi rê chuột hoặc bấm, chọn cạnh có hình học gần con trỏ nhất (tính bằng pixel) và tô sáng trước đúng
   * cạnh đó, để người dùng thấy sẽ đóng gì.
   */
  private addHitSegments(segs: RouteSegment[], onSegmentClick: (seg: RouteSegment) => void) {
    const preview = L.layerGroup().addTo(this.routes)
    const showPreview = (seg: RouteSegment | null) => {
      preview.clearLayers()
      if (seg) {
        L.polyline(seg.latlngs, { color: this.palette.closed, weight: 9, opacity: 0.55, interactive: false }).addTo(preview)
        // Cạnh chỉ dài vài pixel thì nét tô gần như không thấy: thêm chấm ở giữa cạnh để vẫn nhận ra.
        const mid = seg.latlngs[Math.floor(seg.latlngs.length / 2)]
        const first = seg.latlngs[0]
        const at = seg.latlngs.length === 2 ? L.latLng((first.lat + mid.lat) / 2, (first.lng + mid.lng) / 2) : mid
        L.circleMarker(at, { radius: 7, color: this.palette.closed, weight: 3, fillColor: this.palette.surface, fillOpacity: 1, interactive: false })
          .addTo(preview)
      }
    }
    for (const seg of segs) {
      L.polyline(seg.latlngs, { weight: 18, opacity: 0, className: 'route-hit' })
        .bindTooltip('Bấm để đóng đoạn đang tô đỏ', { sticky: true })
        .on('mousemove', (e: L.LeafletMouseEvent) => showPreview(this.nearestSegment(segs, e.containerPoint)))
        .on('mouseout', () => showPreview(null))
        .on('click', (e: L.LeafletMouseEvent) => {
          L.DomEvent.stop(e) // không để cú bấm lọt xuống bản đồ (chọn lại điểm)
          showPreview(null)
          onSegmentClick(this.nearestSegment(segs, e.containerPoint) ?? seg)
        })
        .addTo(this.routes)
    }
  }

  /** Cạnh có hình học gần điểm `p` (toạ độ màn hình) nhất. */
  private nearestSegment(segs: RouteSegment[], p: L.Point): RouteSegment | null {
    let best: RouteSegment | null = null
    let bestDist = Infinity
    for (const seg of segs) {
      const pts = seg.latlngs.map((ll) => this.map.latLngToContainerPoint(ll))
      for (let i = 1; i < pts.length; i++) {
        const dist = L.LineUtil.pointToSegmentDistance(p, pts[i - 1], pts[i])
        if (dist < bestDist) {
          bestDist = dist
          best = seg
        }
      }
    }
    return best
  }

  // Đoạn đang bị đóng: đỏ, nét đứt (DEMO mục 1.2). Gồm cả đoạn người dùng bấm lẫn cạnh đóng sẵn của case.
  setClosed(segments: RouteSegment[]) {
    this.closed.clearLayers()
    for (const seg of segments) {
      L.polyline(seg.latlngs, { color: this.palette.closed, weight: 6, dashArray: '6 6', interactive: false })
        .bindTooltip('Đoạn đường đang đóng')
        .addTo(this.closed)
    }
  }

  /**
   * Kho và điểm giao; `order` là thứ tự id điểm giao của phương án đang chọn (đánh số 1, 2, …).
   * `broken`: id điểm (kể cả 'depot') không đi tới được hoặc không đi ra được khi tour không khả thi; tô đỏ
   * và ghi tên cố định để người xem thấy ngay điểm nào hỏng (review 14/11, UX-4).
   */
  setTourPoints(depot: TourPoint | null, stops: TourPoint[], order?: string[], broken: ReadonlySet<string> = new Set()) {
    this.points.clearLayers()
    if (depot) {
      const color = broken.has(depot.id) ? this.palette.closed : this.palette.source
      this.marker(depot, 'Kho', color, depot.label !== 'Kho' ? depot.label : undefined)
    }
    stops.forEach((s, i) => {
      const n = order ? order.indexOf(s.id) + 1 : i + 1
      const bad = broken.has(s.id)
      L.marker([s.lat, s.lon], {
        icon: L.divIcon({ className: bad ? 'tour-stop tour-stop-broken' : 'tour-stop', html: String(n), iconSize: [24, 24] }),
        title: s.label,
      })
        .bindTooltip(s.label, { direction: 'top', offset: [0, -12], permanent: bad })
        .addTo(this.points)
    })
  }

  /** Thu phóng cho vừa các điểm (kết quả mới hoặc case vừa nạp); không gọi khi chỉ đóng thêm một đoạn. */
  fitTo(points: L.LatLng[]) {
    if (!points.length) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    this.map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 17, animate: !reduce })
  }

  /** Vẽ phương án tour đang chọn; có `onSegmentClick` thì bấm được từng cạnh để đóng đoạn (R1 C5). */
  drawTour(cand: EdgePath & { geometry: { coordinates: [number, number][] } }, onSegmentClick?: (seg: RouteSegment) => void) {
    this.routes.clearLayers()
    const coords = cand.geometry.coordinates
    if (coords.length) {
      L.polyline(toLatLngs(coords), { color: this.palette.tour, weight: 5, opacity: 0.85, interactive: false }).addTo(this.routes)
    }
    if (onSegmentClick) this.addHitSegments(routeSegments(cand), onSegmentClick)
  }

  clearRoutes() {
    this.routes.clearLayers()
  }

  clear() {
    this.points.clearLayers()
    this.routes.clearLayers()
    this.closed.clearLayers()
  }
}
