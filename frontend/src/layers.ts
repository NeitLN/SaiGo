// Các lớp vẽ trên bản đồ Leaflet (docs/DEMO.md mục 1.2): vùng ùn tắc, điểm đi/đến, tuyến Dijkstra và A*,
// đoạn bị đóng (T54), kho và điểm giao của tour (T73).
import L from 'leaflet'
import type { AlgorithmResult, LatLon, RouteResponse, Scenario } from './api'
import { arrowPoints } from './geometry'

// Màu lấy từ token của theme Astryx (đọc trên phần tử bản đồ, nằm trong <Theme>), không viết mã màu cứng.
type Palette = {
  dijkstra: string; astar: string; source: string; target: string; closed: string; zone: string; tour: string; surface: string
  road: string; casing: string; zoneBorder: string; success: string
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
    // Viền vùng: vàng cảnh báo trên nền xám chỉ 1,09:1; viền dùng token viền cảnh báo (~4:1) (test lại 15/11, A-2).
    zoneBorder: v('--color-border-warning'),
    tour: v('--color-data-categorical-purple'),
    surface: v('--color-background-card'),
    road: v('--color-text-secondary'),
    // Viền tối dưới tuyến: tuyến cam của A* trên nền xám chỉ đạt 2,29:1, dưới mức 3:1 (FE-5, WCAG 1.4.11).
    casing: v('--color-text-primary'),
    // Pin điểm đi: xanh của token success (3,47:1 trên nền Esri), không dùng xanh lá categorical (2,77:1) (đợt UI 15/11).
    success: v('--color-success'),
  }
  probe.remove()
  return palette
}

// Tên loại đường OSM trong luật ùn tắc, ghi tiếng Việt trên nhãn vùng (D-8).
const ROAD_KIND: Record<string, string> = {
  motorway: 'cao tốc', trunk: 'trục chính', primary: 'đường chính', secondary: 'đường cấp 2', tertiary: 'đường cấp 3',
  residential: 'đường nội khu', unclassified: 'đường nhỏ',
}

/** Cấp đường cho nền rút gọn: 2 = trục chính, 1 = đường cấp 2–3, 0 = còn lại. */
export function roadLevel(kind: string | null): 0 | 1 | 2 {
  const k = (kind ?? '').replace(/_link$/, '')
  if (k === 'motorway' || k === 'trunk' || k === 'primary') return 2
  if (k === 'secondary' || k === 'tertiary') return 1
  return 0
}
// [viền, lõi] (px ở z16) theo cấp đường.
const ROAD_WIDTH: Record<number, [number, number]> = { 0: [3.5, 2], 1: [5.5, 3.5], 2: [8, 6] }

/** Màu đậm hơn cùng sắc (viền tuyến, đợt UI 15/11): nhân kênh RGB với k; nhận "rgb(...)" / "rgba(...)" như readPalette trả. */
export function shade(color: string, k: number): string {
  const m = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (!m) return color
  const [r, g, b] = m.slice(1, 4).map((x) => Math.round(Number(x) * k))
  return `rgb(${r}, ${g}, ${b})`
}

/** Câu đầy đủ của các vùng ùn tắc cho chú giải (trên bản đồ chỉ để nhãn ngắn "×2"). */
export function zoneLegend(scenario: Scenario): string {
  const parts = scenario.rules.filter((r) => r.zone.type === 'circle').map((r) => {
    const kinds = [...new Set((r.highway ?? []).map((h) => ROAD_KIND[h.replace(/_link$/, '')] ?? h))]
    return `×${r.alpha.toLocaleString('vi-VN')}${kinds.length ? ` ${kinds.join(', ')}` : ''}`
  })
  return `Vùng cao điểm mô phỏng${parts.length ? `: ${parts.join('; ')}` : ''}`
}

// Pin điểm đi/đến (SVG, viền trắng, bóng nhẹ trong globals.css): neo ở mũi pin.
const pinHtml = (fill: string) => `<svg width="28" height="36" viewBox="0 0 28 36" aria-hidden="true">`
  + `<path d="M14 34.5s10.5-10.6 10.5-19.5a10.5 10.5 0 1 0-21 0c0 8.9 10.5 19.5 10.5 19.5z" fill="${fill}" stroke="white" stroke-width="2.5"/>`
  + `<circle cx="14" cy="15" r="4.2" fill="white"/></svg>`
// Chevron chỉ chiều, trắng, đặt trên nét tuyến (thay ký tự "▲").
const chevronHtml = (deg: number) => `<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" style="transform:rotate(${deg.toFixed(0)}deg)">`
  + `<path d="M2.5 8.5 L6 3.5 L9.5 8.5" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`
export type LegendKind = 'dijkstra' | 'astar' | 'same' | 'zone' | 'closed' | 'previous' | 'trace' | 'tour' | 'broken' | 'point'
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

/** Độ dài một đoạn (mét), cho danh sách đóng đoạn bằng bàn phím. */
export function segmentLength(seg: RouteSegment): number {
  let m = 0
  for (let i = 1; i < seg.latlngs.length; i++) m += seg.latlngs[i - 1].distanceTo(seg.latlngs[i])
  return m
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
  private networkRenderer: L.Canvas | null = null
  private quietHitsFor: object | null = null   // kết quả vừa bấm đóng đoạn: chưa gắn lại gợi ý (addHitSegments)
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
    // Nút "Về toàn tuyến" dưới nút zoom; ẩn khi chưa có kết quả.
    const fitBar = L.DomUtil.create('div', 'leaflet-bar leaflet-control')
    const fitBtn = L.DomUtil.create('a', 'map-fit', fitBar) as HTMLAnchorElement
    fitBtn.href = '#'
    fitBtn.title = 'Về toàn tuyến'
    fitBtn.setAttribute('role', 'button')
    fitBtn.setAttribute('aria-label', 'Về toàn tuyến')
    fitBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    L.DomEvent.disableClickPropagation(fitBar)
    L.DomEvent.on(fitBtn, 'click', (e) => {
      L.DomEvent.preventDefault(e)
      if (this.lastFit) this.fitTo(this.lastFit.points, this.lastFit.rightPad)
    })
    fitBar.style.display = 'none'
    this.fitButton = fitBtn
    const Fit = L.Control.extend({ onAdd: () => fitBar })
    new Fit({ position: 'topleft' }).addTo(map)    // Node đã mở rộng: dưới tuyến (overlayPane z 400), trên tuyến lần trước; canvas vì có thể vài nghìn chấm.
    const tracePane = map.createPane('trace')
    tracePane.style.zIndex = '395'
    tracePane.style.pointerEvents = 'none'
    // Một renderer dùng chung: tạo mới mỗi lần vẽ thì Leaflet giữ lại canvas cũ (review #139: 10 canvas sau vài lần).
    this.traceRenderer = L.canvas({ pane: 'trace' })
    this.trace.addTo(map)
    // Mũi tên chiều của tour: trên tuyến, dưới mọi marker (test lại 15/11, T-2: chung markerPane thì mũi tên xếp theo
    // vĩ độ và đè lên số "3", ô "K").
    const arrowPane = map.createPane('arrows')
    arrowPane.style.zIndex = '420'
    arrowPane.style.pointerEvents = 'none'
    // Đoạn đóng: trên tuyến và mũi tên, dưới marker (R-1, T-3): trước đây chung overlayPane nên tuyến vẽ sau che nét
    // đỏ trong lúc chờ kết quả. Không đặt trên marker vì sẽ che số điểm giao (góp ý #152); cạnh ngắn sát một điểm thì
    // tour không khả thi tự thu phóng vào đó (App) nên vẫn thấy.
    const closedPane = map.createPane('closed')
    closedPane.style.zIndex = '440'
    closedPane.style.pointerEvents = 'none'
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
  setNetwork(lines: [number, number][][] | null, kinds?: (string | null)[]) {
    if (this.network) this.network.remove()
    // Gỡ cả renderer: gỡ polyline thôi thì canvas vẫn nằm lại, mỗi lần bật lại thêm một canvas.
    if (this.networkRenderer) this.networkRenderer.remove()
    this.map.off('zoomend', this.restyleNetwork)
    this.map.getContainer().classList.remove('map-fallback')
    this.network = null
    this.networkRenderer = null
    if (!lines) return     // tile tải lại được: gỡ nền dự phòng (MapView)
    const pane = this.map.getPane('basemap') ?? this.map.createPane('basemap')
    pane.style.zIndex = '250'
    pane.style.pointerEvents = 'none'
    const renderer = L.canvas({ pane: 'basemap' })
    this.networkRenderer = renderer
    // Nền rút gọn trông như bản đồ thật (đợt UI 15/11): đường trắng có viền xám trên nền xám nhạt, chia ba cấp theo
    // loại đường OSM (`kinds` từ /api/network); vẽ cấp nhỏ trước, cấp lớn đè lên. Backend cũ không có `kinds` thì mọi
    // đường là cấp nhỏ. Không có tên đường: dữ liệu đồ thị không lưu tên.
    const groups: [number, number][][][] = [[], [], []]
    lines.forEach((ln, i) => groups[roadLevel(kinds?.[i] ?? null)].push(ln))
    const group = L.layerGroup()
    this.networkStyles = []
    groups.forEach((g, level) => {
      if (!g.length) return
      const latlngs = g.map(toLatLngs)
      const [casingW, coreW] = ROAD_WIDTH[level]
      const casing = L.polyline(latlngs, {
        pane: 'basemap', renderer, color: this.palette.road, opacity: 0.35, weight: casingW, interactive: false,
        lineCap: 'round', lineJoin: 'round',
      }).addTo(group)
      const core = L.polyline(latlngs, {
        pane: 'basemap', renderer, color: this.palette.surface, opacity: 1, weight: coreW, interactive: false,
        lineCap: 'round', lineJoin: 'round',
      }).addTo(group)
      this.networkStyles.push([casing, casingW], [core, coreW])
    })
    // Vẽ lõi sau mọi viền để chỗ giao nhau liền mạch như bản đồ thật.
    for (const [layer] of this.networkStyles.filter((_, i) => i % 2 === 1)) (layer as L.Polyline).bringToFront()
    this.network = group.addTo(this.map)
    this.map.getContainer().classList.add('map-fallback')
    this.restyleNetwork()
    this.map.on('zoomend', this.restyleNetwork)
  }

  // Độ dày đường theo mức zoom: chuẩn ở z16, gấp đôi mỗi mức (giới hạn để không phủ kín bản đồ).
  private networkStyles: [L.Polyline, number][] = []
  private restyleNetwork = () => {
    const k = Math.min(4, Math.max(0.35, 2 ** (this.map.getZoom() - 16)))
    for (const [layer, w] of this.networkStyles) layer.setStyle({ weight: w * k })
  }

  // Vùng ùn tắc của kịch bản: hình tròn tô nhạt, không bấm được để không chặn thao tác chọn điểm.
  setZones(scenario: Scenario) {
    this.zones.clearLayers()
    for (const rule of scenario.rules) {
      const z = rule.zone
      if (z.type !== 'circle') continue // chỉ biết vẽ vùng tròn (CongestionZone)
      // Đợt UI 15/11: viền liền mảnh, tô rất nhạt để không làm đục bản đồ; nét đứt để dành cho A* và đoạn đóng.
      L.circle([z.lat, z.lon], {
        radius: z.radius_m, color: this.palette.zoneBorder, weight: 2, fillColor: this.palette.zone, fillOpacity: 0.08,
        interactive: false,
      }).addTo(this.zones)
      // Nhãn ở mép trên vòng tròn thay vì ở tâm, để không đè lên tuyến đi qua giữa vùng (UX-2); nằm phía trong vòng
      // (direction bottom) để không lọt ra ngoài mép trên bản đồ, dưới thanh header (test lại 15/11, D-8).
      const topLat = z.lat + z.radius_m / 111_320
      L.tooltip({ permanent: true, direction: 'bottom', className: 'zone-label', interactive: false })
        .setLatLng([topLat, z.lon])
        // Nhãn ngắn; loại đường áp dụng ghi ở chú giải (zoneLegend).
        .setContent(`Cao điểm mô phỏng ×${rule.alpha.toLocaleString('vi-VN')}`)
        .addTo(this.zones)
    }
  }

  private marker(p: LatLon, label: string, color: string, snapM?: number) {
    // Pin SVG (đợt UI 15/11) thay vòng rỗng 7 px. Bấm vào marker không lan xuống bản đồ (không chọn lại điểm, không
    // đóng đoạn): marker của Leaflet mặc định không chuyển sự kiện chuột cho bản đồ; listener rỗng để chắc chắn.
    // Khoảng cách snap chỉ ghi khi đáng kể (> 15 m); "cách 0 m" chỉ gây nhiễu.
    const far = snapM !== undefined && snapM > 15
    const m = L.marker([p.lat, p.lon], {
      icon: L.divIcon({ className: 'map-pin', html: pinHtml(color), iconSize: [28, 36], iconAnchor: [14, 35] }),
      pane: 'points', keyboard: false, title: label,
    })
      .on('click', () => {})
      .bindTooltip(far ? `${label} · cách ${snapM.toFixed(0)} m` : label,
        { permanent: true, direction: 'top', offset: [0, -34], className: 'map-label' })
      .addTo(this.points)
    m.getElement()?.setAttribute('role', 'img')
    m.getElement()?.setAttribute('aria-label', label === 'Đi' ? 'Điểm đi' : 'Điểm đến')
    return m
  }

  // Điểm người dùng bấm, trước khi có kết quả.
  setPoints(source: LatLon | null, target: LatLon | null) {
    this.points.clearLayers()
    if (source) this.marker(source, 'Đi', this.palette.success)
    if (target) this.marker(target, 'Đến', this.palette.closed)
  }

  // Sau khi có kết quả: marker đặt tại node đã snap, tooltip ghi khoảng cách snap.
  setSnapped(res: RouteResponse) {
    this.points.clearLayers()
    const { source: s, target: t } = res.snapped
    this.marker(s, 'Đi', this.palette.success, s.snap_distance_m)
    this.marker(t, 'Đến', this.palette.closed, t.snap_distance_m)
  }

  /**
   * Vẽ tuyến Dijkstra và A* (trùng nhau thì một nét có viền, ARCHITECTURE mục 6). Khi có `onSegmentClick`,
   * mỗi cạnh của tuyến Dijkstra có một nét trong suốt rộng để bấm đóng đoạn (T54).
   */
  drawRoutes(res: RouteResponse, onSegmentClick?: (seg: RouteSegment) => void) {
    this.routes.clearLayers()
    const d = res.results.dijkstra
    const a = res.results.astar
    // Đợt UI 15/11: viền cùng sắc đậm hơn (không còn ba lớp xanh/cam/đen như sợi cáp); trùng tuyến là một nét xanh,
    // chú giải ghi rõ cả hai thuật toán; chevron trắng chỉ chiều. Viền đậm giữ tương phản ≥ 3:1 trên nền xám.
    const line = (ll: L.LatLng[], color: string, casingW: number, coreW: number, dash?: string) => {
      L.polyline(ll, { color: shade(color, 0.55), weight: casingW, interactive: false, lineCap: 'round', lineJoin: 'round' })
        .addTo(this.routes)
      L.polyline(ll, { color, weight: coreW, dashArray: dash, interactive: false, lineCap: 'round', lineJoin: 'round' })
        .addTo(this.routes)
    }
    if (sameRoute(d, a)) {
      line(toLatLngs(d!.geometry.coordinates), this.palette.dijkstra, 10, 6)
      this.chevrons(d!.geometry.coordinates)
    } else {
      if (d?.status === 'ok') {
        line(toLatLngs(d.geometry.coordinates), this.palette.dijkstra, 10, 6)
        this.chevrons(d.geometry.coordinates)
      }
      if (a?.status === 'ok') line(toLatLngs(a.geometry.coordinates), this.palette.astar, 7, 4, '8 6')
    }
    this.setFitButton(true)
    if (onSegmentClick && d) this.addHitSegments(routeSegments(d), onSegmentClick, res)
  }

  /**
   * Vùng bấm để đóng đoạn trên tuyến hoặc tour (T54, R1). Cạnh ngắn chỉ dài vài pixel nên vùng bấm 18 px
   * của các cạnh kề nhau chồng lên nhau, và nét vẽ sau sẽ "ăn" cú bấm. Vì vậy không tin nét nào nằm trên:
   * khi rê chuột hoặc bấm, chọn cạnh có hình học gần con trỏ nhất (tính bằng pixel) và tô sáng trước đúng
   * cạnh đó, để người dùng thấy sẽ đóng gì.
   */
  private addHitSegments(segs: RouteSegment[], onSegmentClick: (seg: RouteSegment) => void, source: object) {
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
    const hits: L.Polyline[] = []
    for (const seg of segs) {
      const hit = L.polyline(seg.latlngs, { weight: 18, opacity: 0, className: 'route-hit' })
      hits.push(hit)
      // Sau khi bấm đóng một đoạn, tuyến cũ được vẽ lại ngay (để hiện nét đỏ) trong lúc chờ kết quả; vùng bấm mới nằm
      // dưới con trỏ nên gợi ý mở lại. Không gắn gợi ý cho tới khi có kết quả mới (test lại 15/11).
      if (this.quietHitsFor !== source) hit.bindTooltip('Bấm để đóng đoạn đang tô đỏ', { sticky: true })
      hit
        .on('mousemove', (e: L.LeafletMouseEvent) => showPreview(this.nearestSegment(segs, e.containerPoint)))
        .on('mouseout', () => showPreview(null))
        .on('click', (e: L.LeafletMouseEvent) => {
          L.DomEvent.stop(e) // không để cú bấm lọt xuống bản đồ (chọn lại điểm)
          showPreview(null)
          // Bỏ gợi ý "Bấm để đóng…" ngay, không để tới khi rê chuột đi (test lại 15/11); vùng bấm chồng nhau nên gỡ
          // ở mọi nét, không chỉ nét được bấm.
          for (const h of hits) h.unbindTooltip()
          this.quietHitsFor = source
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
      // Viền sáng dưới nét đỏ để nét đứt vẫn đọc được khi đè lên tuyến hay marker.
      L.polyline(seg.latlngs, { pane: 'closed', color: this.palette.surface, weight: 9, opacity: 0.9, interactive: false })
        .addTo(this.closed)
      L.polyline(seg.latlngs, { pane: 'closed', color: this.palette.closed, weight: 6, dashArray: '6 6', interactive: false })
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
    // Bản đồ hẹp (điện thoại): tên cố định của 5–14 điểm đè lên nhau (test lại 15/11, A-10), nên chỉ hiện khi chạm /
    // rê chuột; điểm hỏng vẫn ghi tên cố định.
    const w = this.map.getSize().x
    const narrow = w > 0 && w < 600
    // Tên đọc được cho trình đọc màn hình (A-4): "Điểm 1: Nhà hát Thành phố", kho cũng có tên.
    const label = (m: L.Marker, text: string, bad: boolean) => {
      const el = m.getElement()
      el?.setAttribute('role', 'img')
      el?.setAttribute('aria-label', bad ? `${text} (không đi được)` : text)
    }
    if (depot) {
      // Kho dùng ô vuông riêng, không còn là vòng tròn xanh giống hệt "Điểm đi" (review 14/11 đợt 3, UX-9).
      const bad = broken.has(depot.id)
      const dm = L.marker([depot.lat, depot.lon], {
        icon: L.divIcon({ className: bad ? 'tour-depot tour-stop-broken' : 'tour-depot', html: 'K', iconSize: [26, 26] }),
        title: depot.label, keyboard: false,
      })
        .bindTooltip(depot.label !== 'Kho' ? `Kho · ${depot.label}` : 'Kho', { permanent: true, direction: 'top', offset: [0, -16], className: 'map-label' })
        .addTo(this.points)
      label(dm, depot.label !== 'Kho' ? `Kho: ${depot.label}` : 'Kho', bad)
    }
    stops.forEach((s, i) => {
      const n = order ? order.indexOf(s.id) + 1 : i + 1
      const bad = broken.has(s.id)
      // keyboard: false: marker không làm gì khi bấm, nên không để là nút nhận Tab với tên "1" (test lại 15/11, A-4).
      const sm = L.marker([s.lat, s.lon], {
        icon: L.divIcon({ className: bad ? 'tour-stop tour-stop-broken' : 'tour-stop', html: String(n), iconSize: [24, 24] }),
        title: s.label, keyboard: false,
      })
        // Điểm có tên (case demo) thì hiện tên cố định cạnh số; tên mặc định "Điểm n" thì chỉ hiện khi rê chuột.
        .bindTooltip(s.label, { direction: 'right', offset: [12, 0], permanent: bad || (!/^Điểm \d+$/.test(s.label) && !narrow), className: 'stop-label' })
        .addTo(this.points)
      label(sm, `Điểm ${n}: ${s.label}`, bad)
    })
  }

  /** Thu phóng cho vừa các điểm (kết quả mới hoặc case vừa nạp); không gọi khi chỉ đóng thêm một đoạn. */
  fitTo(points: L.LatLng[], rightPad = 40) {
    if (!points.length) return
    // Bản đồ vừa tạo lại khi đổi bố cục có thể chưa có kích thước (0 px): fitBounds lúc đó ra mức zoom sai và không
    // ai thu phóng lại (test lại 15/11, A-10). Đợi lần đổi kích thước đầu tiên rồi mới thu phóng.
    const size = this.map.getSize()
    if (size.x === 0 || size.y === 0) {
      this.map.once('resize', () => this.fitTo(points, rightPad))
      return
    }
    this.lastFit = { points, rightPad }
    this.setFitButton(true)
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    // rightPad: chừa chỗ cho nhãn tên điểm đặt bên phải marker (tour), để tên không bị cắt ở mép.
    this.map.fitBounds(L.latLngBounds(points), {
      paddingTopLeft: [40, 40], paddingBottomRight: [rightPad, 40], maxZoom: 17, animate: !reduce,
    })
  }

  /** Vẽ phương án tour đang chọn; có `onSegmentClick` thì bấm được từng cạnh để đóng đoạn (R1 C5). */
  drawTour(cand: EdgePath & { geometry: { coordinates: [number, number][] } }, onSegmentClick?: (seg: RouteSegment) => void) {
    this.routes.clearLayers()
    const coords = cand.geometry.coordinates
    if (coords.length) {
      const ll = toLatLngs(coords)
      L.polyline(ll, { color: shade(this.palette.tour, 0.6), weight: 9, interactive: false, lineCap: 'round', lineJoin: 'round' })
        .addTo(this.routes)
      L.polyline(ll, { color: this.palette.tour, weight: 6, interactive: false, lineCap: 'round', lineJoin: 'round' }).addTo(this.routes)
      // Chevron chỉ chiều mỗi ~200 m (UX-9): đoạn đi và về chồng lên nhau vẫn đọc được chiều.
      this.chevrons(coords, 200)
      this.setFitButton(true)
    }
    if (onSegmentClick) this.addHitSegments(routeSegments(cand), onSegmentClick, cand)
  }

  /**
   * Viền vùng có dữ liệu (review 14/11 đợt 2, PM-7/UX-3): khung bao mọi node, nét đứt xám, không bấm được.
   * Người dùng thấy ngay đặt điểm ở đâu thì snap được, thay vì bấm ra ngoài rồi mới bị báo lỗi.
   * Đợt UI 15/11: phủ mờ phần ngoài khung thay cho nét gạch đen cắt ngang bản đồ (trông như lỗi), viền mảnh liền;
   * giới hạn kéo bản đồ quanh vùng để không lạc ra ngoài lúc demo. Khung chỉ là "vùng có dữ liệu", không có nghĩa mọi
   * điểm bên trong đều đi được (điểm vẫn được kiểm khi đặt).
   */
  setDataArea(b: { south: number; west: number; north: number; east: number } | null) {
    this.area.clearLayers()
    if (!b) return
    const inner: L.LatLngTuple[] = [[b.south, b.west], [b.north, b.west], [b.north, b.east], [b.south, b.east]]
    const pad = 0.5
    const outer: L.LatLngTuple[] = [[b.south - pad, b.west - pad], [b.north + pad, b.west - pad],
      [b.north + pad, b.east + pad], [b.south - pad, b.east + pad]]
    L.polygon([outer, inner], {
      pane: 'previous', stroke: false, fillColor: this.palette.casing, fillOpacity: 0.08, interactive: false,
    }).addTo(this.area)
    L.rectangle([[b.south, b.west], [b.north, b.east]], {
      pane: 'previous', color: this.palette.road, weight: 1.5, opacity: 0.7, fill: false, interactive: false,
    }).addTo(this.area)
    this.map.setMaxBounds(L.latLngBounds([b.south, b.west], [b.north, b.east]).pad(0.6))
    this.map.setMinZoom(13)
  }

  /** Tuyến của lần trước (cùng điểm, khác kịch bản/cạnh đóng): nét xám mờ làm mốc so (review 14/11 đợt 2, AI-7). */
  setPrevious(coords: [number, number][] | null) {
    this.previous.clearLayers()
    if (!coords?.length) return
    // Nét "rỗng" (viền xám, lõi trắng): đọc như bóng của tuyến cũ, không như một con đường to (đợt UI 15/11).
    const ll = toLatLngs(coords)
    L.polyline(ll, { pane: 'previous', color: this.palette.road, weight: 8, opacity: 0.6, lineCap: 'round', interactive: false })
      .addTo(this.previous)
    L.polyline(ll, { pane: 'previous', color: this.palette.surface, weight: 4, lineCap: 'round', interactive: false })
      .addTo(this.previous)
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
      dijkstra: this.swatchLine(this.palette.dijkstra, false, shade(this.palette.dijkstra, 0.55)),
      astar: this.swatchLine(this.palette.astar, true, shade(this.palette.astar, 0.55)),
      same: this.swatchLine(this.palette.dijkstra, false, shade(this.palette.dijkstra, 0.55)),
      // Tô nhạt như trên bản đồ (fillOpacity 0.1), viền đậm (góp ý #143).
      zone: `<i class="legend-area" style="border-color:${this.palette.zoneBorder};background:color-mix(in srgb, ${this.palette.zone} 15%, transparent)"></i>`,
      closed: this.swatchLine(this.palette.closed, true),
      previous: this.swatchLine(this.palette.surface, false, this.palette.road),
      trace: `<i class="legend-dot" style="background:${this.palette.dijkstra}"></i><i class="legend-dot" style="background:${this.palette.astar}"></i>`,
      tour: this.swatchLine(this.palette.tour, false, shade(this.palette.tour, 0.6)),
      broken: `<i class="legend-dot" style="background:${this.palette.closed}"></i>`,
      point: `<i class="legend-pin" style="background:${this.palette.success}"></i><i class="legend-pin" style="background:${this.palette.closed}"></i>`,
    }
    this.legendEl.innerHTML = '<div class="legend-title">Chú giải</div>' + items.map((it) => `<div class="legend-row">${sw[it.kind]}<span>${escapeHtml(it.label)}</span></div>`).join('')
    this.legendEl.style.display = items.length ? '' : 'none'
  }

  private swatchLine(color: string, dashed = false, outline?: string) {
    const style = `border-top-color:${color};border-top-style:${dashed ? 'dashed' : 'solid'}${outline ? `;box-shadow:0 0 0 2px ${outline}` : ''}`
    return `<i class="legend-line" style="${style}"></i>`
  }

  /** Chevron trắng chỉ chiều dọc tuyến (pane arrows: trên tuyến, dưới marker và đoạn đóng). */
  private chevrons(coords: [number, number][], everyM = 250) {
    for (const a of arrowPoints(coords, everyM)) {
      const m = L.marker([a.lat, a.lon], {
        icon: L.divIcon({ className: 'route-chevron', html: chevronHtml(a.bearing), iconSize: [12, 12] }),
        interactive: false, keyboard: false, pane: 'arrows',
      }).addTo(this.routes)
      m.getElement()?.setAttribute('aria-hidden', 'true')   // trình đọc màn hình không đọc từng mũi tên (A-4)
    }
  }

  // Nút "Về toàn tuyến" (đợt UI 15/11): thu phóng lại vừa kết quả đang hiện sau khi người dùng kéo / phóng bản đồ.
  private lastFit: { points: L.LatLng[]; rightPad: number } | null = null
  private fitButton: HTMLAnchorElement | null = null
  private setFitButton(on: boolean) {
    if (this.fitButton) this.fitButton.parentElement!.style.display = on && this.lastFit ? '' : 'none'
  }

  clearRoutes() {
    this.routes.clearLayers()
    this.setFitButton(false)
  }

  clear() {
    this.points.clearLayers()
    this.routes.clearLayers()
    this.closed.clearLayers()
  }
}
