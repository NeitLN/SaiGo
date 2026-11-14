// Các lớp vẽ trên bản đồ Leaflet (docs/DEMO.md mục 1.2): vùng ùn tắc, điểm đi/đến, tuyến Dijkstra và A*,
// đoạn bị đóng (T54), kho và điểm giao của tour (T73).
import L from 'leaflet'
import type { AlgorithmResult, LatLon, RouteResponse, Scenario } from './api'

// Màu lấy từ token của theme Astryx (đọc trên phần tử bản đồ, nằm trong <Theme>), không viết mã màu cứng.
type Palette = {
  dijkstra: string; astar: string; source: string; target: string; closed: string; zone: string; tour: string; surface: string
  road: string; casing: string
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
    // Vùng ùn tắc dùng màu cảnh báo, không dùng cam của A* (review 14/11 đợt 3, UX-2: hai nghĩa cùng một màu).
    zone: v('--color-warning'),
    tour: v('--color-data-categorical-purple'),
    surface: v('--color-background-card'),
    road: v('--color-text-secondary'),
    // Viền tối dưới tuyến: tuyến cam của A* trên nền xám chỉ đạt 2,29:1, dưới mức 3:1 (FE-5, WCAG 1.4.11).
    casing: v('--color-text-primary'),
  }
  probe.remove()
  return palette
}

export type LegendKind = 'dijkstra' | 'astar' | 'same' | 'zone' | 'closed' | 'previous' | 'trace' | 'tour' | 'broken'
export interface LegendItem { kind: LegendKind; label: string }

const escapeHtml = (s: string) => s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)

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
  private previous = L.layerGroup()
  private area = L.layerGroup()
  private trace = L.layerGroup()
  private traceRenderer: L.Canvas
  private palette: Palette
  private map: L.Map
  private legendEl: HTMLDivElement

  constructor(map: L.Map) {
    this.map = map
    this.palette = readPalette(map.getContainer())
    // Marker điểm đi/đến/kho nằm trong pane riêng, trên vùng bấm 18 px của tuyến (overlayPane, z 400) và dưới
    // marker điểm giao (markerPane, z 600). Nếu chung pane, vùng bấm vẽ sau sẽ đè lên marker: bấm vào marker
    // "Đi" lại đóng mất cạnh đầu tuyến (QA-8).
    map.createPane('points').style.zIndex = '450'
    // Tuyến lần trước (so trước/sau) nằm dưới mọi lớp vẽ khác (overlayPane z 400) và không bấm được.
    const prevPane = map.createPane('previous')
    prevPane.style.zIndex = '390'
    prevPane.style.pointerEvents = 'none'
    this.previous.addTo(map)
    this.area.addTo(map)
    this.legendEl = L.DomUtil.create('div', 'map-legend')
    this.legendEl.style.display = 'none'
    // Bấm hay cuộn trên chú giải không lan xuống bản đồ (review #143: bấm chú giải từng đặt điểm, cuộn thì zoom).
    L.DomEvent.disableClickPropagation(this.legendEl)
    L.DomEvent.disableScrollPropagation(this.legendEl)
    const legendEl = this.legendEl
    const Legend = L.Control.extend({ onAdd: () => legendEl })
    new Legend({ position: 'bottomleft' }).addTo(map)
    // Node đã mở rộng: dưới tuyến (overlayPane z 400), trên tuyến lần trước; canvas vì có thể vài nghìn chấm.
    const tracePane = map.createPane('trace')
    tracePane.style.zIndex = '395'
    tracePane.style.pointerEvents = 'none'
    // Một renderer dùng chung: tạo mới mỗi lần vẽ thì Leaflet giữ lại canvas cũ (review #139: 10 canvas sau vài lần).
    this.traceRenderer = L.canvas({ pane: 'trace' })
    this.trace.addTo(map)
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
        radius: z.radius_m, color: this.palette.zone, weight: 2, dashArray: '6 6', fillColor: this.palette.zone, fillOpacity: 0.1,
        interactive: false,
      }).addTo(this.zones)
      // Nhãn ở mép trên vòng tròn thay vì ở tâm, để không đè lên tuyến đi qua giữa vùng (UX-2).
      const topLat = z.lat + z.radius_m / 111_320
      L.tooltip({ permanent: true, direction: 'top', className: 'zone-label', interactive: false })
        .setLatLng([topLat, z.lon])
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
    const casing = (ll: L.LatLng[], weight: number) =>
      L.polyline(ll, { color: this.palette.casing, weight, opacity: 0.35, interactive: false }).addTo(this.routes)
    if (sameRoute(d, a)) {
      const latlngs = toLatLngs(d!.geometry.coordinates)
      casing(latlngs, 13)
      L.polyline(latlngs, { color: this.palette.astar, weight: 10, opacity: 0.9, interactive: false }).addTo(this.routes)
      L.polyline(latlngs, { color: this.palette.dijkstra, weight: 5, interactive: false }).addTo(this.routes)
    } else {
      if (d?.status === 'ok') {
        casing(toLatLngs(d.geometry.coordinates), 9)
        L.polyline(toLatLngs(d.geometry.coordinates), { color: this.palette.dijkstra, weight: 6, opacity: 0.8, interactive: false })
          .addTo(this.routes)
      }
      if (a?.status === 'ok') {
        casing(toLatLngs(a.geometry.coordinates), 7)
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

  /**
   * Viền vùng có dữ liệu (review 14/11 đợt 2, PM-7/UX-3): khung bao mọi node, nét đứt xám, không bấm được.
   * Người dùng thấy ngay đặt điểm ở đâu thì snap được, thay vì bấm ra ngoài rồi mới bị báo lỗi.
   */
  setDataArea(b: { south: number; west: number; north: number; east: number } | null) {
    this.area.clearLayers()
    if (!b) return
    L.rectangle([[b.south, b.west], [b.north, b.east]], {
      pane: 'previous', color: this.palette.road, weight: 2, dashArray: '8 6', fill: false, interactive: false,
    }).addTo(this.area)
  }

  /** Tuyến của lần trước (cùng điểm, khác kịch bản/cạnh đóng): nét xám mờ làm mốc so (review 14/11 đợt 2, AI-7). */
  setPrevious(coords: [number, number][] | null) {
    this.previous.clearLayers()
    if (!coords?.length) return
    L.polyline(toLatLngs(coords), {
      pane: 'previous', color: this.palette.road, weight: 9, opacity: 0.45, lineCap: 'round', interactive: false,
    }).addTo(this.previous)
  }

  /**
   * Node Dijkstra và A* đã mở rộng (review 14/11 đợt 2, lớp tĩnh có công tắc): Dijkstra chấm xanh lớn hơn, A* chấm
   * cam nhỏ vẽ đè lên, để thấy vùng Dijkstra lan rộng còn A* kéo dài về phía đích. Không animation (D12).
   */
  setTrace(dijkstra: [number, number][] | null, astar: [number, number][] | null) {
    this.trace.clearLayers()
    const renderer = this.traceRenderer
    const dots = (coords: [number, number][] | null, color: string, radius: number) => {
      for (const ll of toLatLngs(coords ?? [])) {
        L.circleMarker(ll, { renderer, pane: 'trace', radius, stroke: false, fillColor: color, fillOpacity: 0.55, interactive: false })
          .addTo(this.trace)
      }
    }
    dots(dijkstra, this.palette.dijkstra, 4)
    dots(astar, this.palette.astar, 2.5)
  }

  /**
   * Chú giải nổi góc dưới trái (review 14/11 đợt 3, UX-2): chỉ liệt kê những gì đang vẽ, màu lấy từ cùng palette
   * với các lớp, nên luôn khớp nét trên bản đồ. Rỗng thì ẩn.
   */
  setLegend(items: LegendItem[]) {
    const sw: Record<LegendKind, string> = {
      dijkstra: this.swatchLine(this.palette.dijkstra),
      astar: this.swatchLine(this.palette.astar, true),
      same: this.swatchLine(this.palette.dijkstra, false, this.palette.astar),
      // Tô nhạt như trên bản đồ (fillOpacity 0.1), viền đậm (góp ý #143).
      zone: `<i class="legend-area" style="border-color:${this.palette.zone};background:color-mix(in srgb, ${this.palette.zone} 15%, transparent)"></i>`,
      closed: this.swatchLine(this.palette.closed, true),
      previous: this.swatchLine(this.palette.road),
      trace: `<i class="legend-dot" style="background:${this.palette.dijkstra}"></i><i class="legend-dot" style="background:${this.palette.astar}"></i>`,
      tour: this.swatchLine(this.palette.tour),
      broken: `<i class="legend-dot" style="background:${this.palette.closed}"></i>`,
    }
    this.legendEl.innerHTML = items.map((it) => `<div class="legend-row">${sw[it.kind]}<span>${escapeHtml(it.label)}</span></div>`).join('')
    this.legendEl.style.display = items.length ? '' : 'none'
  }

  private swatchLine(color: string, dashed = false, outline?: string) {
    const style = `border-top-color:${color};border-top-style:${dashed ? 'dashed' : 'solid'}${outline ? `;box-shadow:0 0 0 2px ${outline}` : ''}`
    return `<i class="legend-line" style="${style}"></i>`
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
