// Giao diện SaiGo (T56): bố cục 3 cột theo DEMO mục 1 — điều khiển / bản đồ / kết quả đo được.
// Chế độ "Tìm đường hai điểm" (T14, T52, T53, đóng đoạn đường T54) và "Tour" (T73).
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AppShell } from '@astryxdesign/core/AppShell'
import { Badge } from '@astryxdesign/core/Badge'
import { Banner } from '@astryxdesign/core/Banner'
import { Button } from '@astryxdesign/core/Button'
import { Heading } from '@astryxdesign/core/Heading'
import { HStack } from '@astryxdesign/core/HStack'
import { Layout, LayoutContent, LayoutHeader, LayoutPanel } from '@astryxdesign/core/Layout'
import { SegmentedControl, SegmentedControlItem } from '@astryxdesign/core/SegmentedControl'
import { Selector } from '@astryxdesign/core/Selector'
import { Spinner } from '@astryxdesign/core/Spinner'
import { Switch } from '@astryxdesign/core/Switch'
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'
import { useMediaQuery } from '@astryxdesign/core/hooks'
import {
  BASELINE, MAX_TOUR_STOPS, getDataset, getHealth, getSnap, postRoute, postTour, type BBox,
  type BlockedEdge, type LatLon, type RouteResponse, type Scenario, type TourMethod, type TourResponse,
} from './api'
import { DEMO_CASES, DEMO_DATASET_ID, NAMED_PLACES } from './cases'
import { toLatLngs, type LegendItem, type MapLayers, type RouteSegment, type TourPoint } from './layers'
import MapView from './MapView'
import RouteResults from './RouteResults'
import TourResults from './TourResults'
import { unreachableGroups } from './tourIssues'
import { samePoints, sameIds as sameIdSet } from './compare'

type Mode = 'route' | 'tour'

// Mỗi lần gửi request là một query mới (n tăng); effect hủy request cũ nên chỉ kết quả mới nhất được hiện.
interface RouteQuery { source: LatLon; target: LatLon; scenarioId: string; blocked: number[]; n: number }
// keepOrder (R1): thứ tự điểm giao trước khi đóng đường, để API trả thêm phương án "Giữ thứ tự cũ".
interface TourQuery { depot: TourPoint; stops: TourPoint[]; scenarioId: string; blocked: number[]; keepOrder?: string[]; n: number }

// Lần chạy đã trả về: response kèm kịch bản và cạnh đóng của chính request đó (nhãn, so sánh trước/sau).
type Run<T> = { res: T; scenarioId: string; blocked: number[] }
const routePoints = (r: RouteResponse) => ({ source: r.snapped.source.node_id, target: r.snapped.target.node_id })
const tourPoints = (r: TourResponse) => Object.fromEntries(Object.entries(r.snapped).map(([k, v]) => [k, v.node_id]))
/**
 * Lần trước để so (review 14/11 đợt 2, PM-1/UX-5/AI-7): chỉ khi cùng điểm mà khác kịch bản hoặc khác cạnh đóng.
 * Cùng điểm, cùng tham số (bấm lại Tìm đường) thì giữ mốc cũ; khác điểm thì bỏ mốc.
 */
function nextPrevious<T>(prev: Run<T> | null, next: Run<T>, pts: (r: T) => Record<string, number>, kept: Run<T> | null): Run<T> | null {
  if (!prev || !samePoints(pts(prev.res), pts(next.res))) return null
  if (prev.scenarioId === next.scenarioId && sameIdSet(prev.blocked, next.blocked)) return kept
  return prev
}

// Đủ cho mọi truy vấn trên vùng demo (lớn nhất 1.762 node khi không còn đường); backend giới hạn 5.000.
const TRACE_LIMIT = 5000

/** Chú thích lớp node đã mở rộng: số node của chính lần tìm có trace (bằng số ở bảng vì cùng tham số). */
function traceLegend(r: RouteResponse): string {
  const d = r.results.dijkstra
  const a = r.results.astar
  if (!d || !a) return ''
  const cut = d.trace_truncated || a.trace_truncated ? ' Chỉ vẽ ' + TRACE_LIMIT.toLocaleString('vi-VN') + ' node đầu.' : ''
  return `Đang vẽ ${d.expanded.toLocaleString('vi-VN')} node Dijkstra và ${a.expanded.toLocaleString('vi-VN')} node A* đã mở rộng.${cut}`
}

// Khoảng cách trong thông báo: dưới 1 km ghi mét, từ 1 km ghi km một chữ số (góp ý #142: tránh "280402 m").
const distanceText = (m: number) =>
  m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} km`

// Điểm có thể mang tên (chọn từ danh sách địa danh hoặc từ case): ô điểm đi/đến hiện tên thay cho toạ độ.
type Pt = LatLon & { name?: string }
const fmt = (p: Pt | null) => (p ? (p.name ?? `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`) : '—')
const latLon = (p: LatLon): LatLon => ({ lat: p.lat, lon: p.lon })   // không gửi tên lên API
const sameIds = (a: number[], b: number[]) => a.length === b.length && a.every((x, i) => x === b[i])
// Đóng đoạn = cạnh được bấm và cạnh đối của nó (DATA_MODEL 4.2); bỏ trùng, giữ thứ tự để so sánh được.
const blockedIds = (preset: number[], segs: RouteSegment[]) =>
  [...new Set([...preset, ...segs.flatMap((s) => (s.twinId === null ? [s.edgeId] : [s.edgeId, s.twinId]))])]
// Đoạn đóng để vẽ: cạnh đóng trong response (gồm cả cạnh đóng sẵn của case, QA-3) cộng các đoạn vừa bấm mà
// response chưa có, để nét đỏ hiện ngay khi bấm, không chờ request về (review #135).
const closedToDraw = (fromRes: BlockedEdge[] | undefined, clicked: RouteSegment[]): RouteSegment[] => {
  const drawn = (fromRes ?? []).map((b) => ({ edgeId: b.edge_id, twinId: null, latlngs: toLatLngs(b.geometry) }))
  const ids = new Set(drawn.map((s) => s.edgeId))
  return [...drawn, ...clicked.filter((s) => !ids.has(s.edgeId))]
}

export default function App() {
  const narrow = useMediaQuery('(max-width: 767px)')
  // Ba cột chỉ từ 1366 px: máy chiếu 1280 × 800 dùng bố cục hai cột, bản đồ 920 px thay vì 620 (góp ý #141).
  const medium = useMediaQuery('(max-width: 1365px)')
  const layersRef = useRef<MapLayers | null>(null)
  const [mapReady, setMapReady] = useState(0)
  const onMapReady = useCallback((l: MapLayers) => {
    layersRef.current = l
    // Bản đồ được tạo lại khi đổi bố cục (breakpoint): thu phóng lại cho vừa kết quả đang hiện.
    pendingFit.current = true
    setMapReady((n) => n + 1)
  }, [])

  const [server, setServer] = useState<{ text: string; ok: boolean | null }>({ text: 'Đang kiểm tra server…', ok: null })
  const [datasetId, setDatasetId] = useState<string | null>(null)
  const [dataArea, setDataArea] = useState<BBox | null>(null)   // viền vùng có dữ liệu (PM-7, UX-3)
  const [scenarios, setScenarios] = useState<Scenario[]>([BASELINE])
  const [scenarioNote, setScenarioNote] = useState<string | null>(null)
  const [scenarioId, setScenarioId] = useState('baseline')
  const [mode, setMode] = useState<Mode>('route')
  const [caseId, setCaseId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Gợi ý khi cú bấm bản đồ bị bỏ qua vì đang hiện kết quả (review 14/11, QA-1): bấm trượt không được xoá kết quả.
  const [notice, setNotice] = useState<string | null>(null)

  // Tìm đường hai điểm
  const [source, setSource] = useState<Pt | null>(null)
  const [target, setTarget] = useState<Pt | null>(null)
  const [closed, setClosed] = useState<RouteSegment[]>([])          // đoạn người dùng bấm đóng (T54)
  const [caseBlocked, setCaseBlocked] = useState<number[]>([])      // cạnh đóng sẵn của case demo
  const [routeQuery, setRouteQuery] = useState<RouteQuery | null>(null)
  // Giữ id kịch bản và số cạnh đóng của chính request đã trả về; nhãn tính lúc render từ danh sách kịch bản
  // hiện có, nên nạp lại danh sách không làm gọi lại /api/route (review #103).
  const [route, setRoute] = useState<Run<RouteResponse> | null>(null)
  const [prevRoute, setPrevRoute] = useState<Run<RouteResponse> | null>(null)   // mốc so trước/sau
  // Lớp node đã mở rộng (review 14/11 đợt 2): tắt mặc định. Trace lấy bằng request riêng có trace_limit, vì ghi
  // trace nằm trong vòng lặp đang đo giờ: lấy chung với request chính thì 'Thời gian tính toán' bị đội lên.
  const [showTrace, setShowTrace] = useState(false)
  const [trace, setTrace] = useState<RouteResponse | null>(null)

  // Tour (T73)
  const [depot, setDepot] = useState<TourPoint | null>(null)
  const [stops, setStops] = useState<TourPoint[]>([])
  const [tourQuery, setTourQuery] = useState<TourQuery | null>(null)
  const [tour, setTour] = useState<TourResponse | null>(null)
  // Kịch bản và cạnh đóng của chính request tour đã trả về, để thẻ tour ghi đúng kịch bản (QA-5).
  const [tourScenario, setTourScenario] = useState<{ scenarioId: string; blocked: number[] } | null>(null)
  const [prevTour, setPrevTour] = useState<Run<TourResponse> | null>(null)       // mốc so trước/sau
  const [tourMethod, setTourMethod] = useState<TourMethod | null>(null)
  const [tourClosed, setTourClosed] = useState<RouteSegment[]>([])          // đoạn bấm đóng trên tour (R1 C5)
  const [tourCaseBlocked, setTourCaseBlocked] = useState<number[]>([])      // cạnh đóng sẵn của case tour (R1 C7)

  const scenario = scenarios.find((s) => s.id === scenarioId) ?? BASELINE
  const blocked = useMemo(() => blockedIds(caseBlocked, closed), [closed, caseBlocked])
  const tourBlocked = useMemo(() => blockedIds(tourCaseBlocked, tourClosed), [tourClosed, tourCaseBlocked])
  // Thứ tự của phương án đang xem; lúc người dùng bấm đóng một đoạn thì đây là "thứ tự cũ" gửi lên API.
  const shownTourOrder = useRef<string[] | undefined>(undefined)
  shownTourOrder.current = tour && tourMethod ? tour.candidates[tourMethod]?.stop_order : undefined
  const keepOrderOnClose = useRef<string[] | undefined>(undefined)
  // Bật khi nạp case, bấm Tìm đường hoặc Lập tour: kết quả kế tiếp sẽ được thu phóng cho vừa (QA-2). Không bật
  // khi đóng đoạn hay đổi kịch bản, để bản đồ không nhảy giữa lúc thao tác.
  const pendingFit = useRef(false)
  // Kết quả đang hiện, đọc trong .then để chọn mốc so trước/sau mà không đưa state vào deps của effect gọi API.
  const routeRef = useRef(route)
  routeRef.current = route
  const prevRouteRef = useRef(prevRoute)
  prevRouteRef.current = prevRoute
  const tourRunRef = useRef<Run<TourResponse> | null>(null)
  tourRunRef.current = tour && tourScenario ? { res: tour, ...tourScenario } : null
  const prevTourRef = useRef(prevTour)
  prevTourRef.current = prevTour
  // Nạp case xoá kết quả đang hiện, nhưng giữ lại làm mốc so cho response đầu tiên của case: nếu case mới cùng bộ
  // điểm (vd. bước 9 → bước 10 của DEMO), response đó vẫn so được với kết quả trước khi đóng đường.
  const carriedRoute = useRef<Run<RouteResponse> | null>(null)
  const carriedTour = useRef<Run<TourResponse> | null>(null)

  // Kiểm lúc mở trang và mỗi khi một request lỗi, để badge không báo "sẵn sàng" khi backend đã tắt.
  const checkServer = useCallback(() => {
    getHealth()
      .then((h) => setServer({ text: h.dataset_loaded ? `Server sẵn sàng · ${h.dataset_id ?? ''}` : 'Server chạy, chưa nạp dataset', ok: h.dataset_loaded }))
      .catch(() => setServer({ text: 'Không kết nối được server', ok: false }))
  }, [])
  const loadDataset = useCallback(() => {
    getDataset()
      .then((d) => {
        if (d === null) {
          setScenarioNote('API chưa có /api/dataset (T51); chỉ có kịch bản cơ sở.')
          return
        }
        setScenarioNote(null)
        setDatasetId(d.dataset_id)
        if (d.scenarios.length) setScenarios(d.scenarios)
        setDataArea(d.bbox ?? null)
      })
      .catch((e: Error) => setScenarioNote(`Không đọc được danh sách kịch bản: ${e.message}`))
  }, [])
  // Request thành công sau khi backend bật lại (kể cả khi mở trang lúc backend còn tắt): đưa badge về
  // "sẵn sàng" và đọc lại danh sách kịch bản, không cần tải lại trang.
  const serverOk = useRef(server.ok)
  serverOk.current = server.ok
  const markServerUp = useCallback(() => {
    if (serverOk.current === true) return
    checkServer()
    loadDataset()
  }, [checkServer, loadDataset])

  useEffect(() => {
    checkServer()
    loadDataset()
  }, [checkServer, loadDataset])

  // --- Gọi API ---

  useEffect(() => {
    if (!routeQuery) return
    const ctl = new AbortController()
    setBusy(true)
    setError(null)
    postRoute({
      source: latLon(routeQuery.source), target: latLon(routeQuery.target), algorithms: ['dijkstra', 'astar'],
      scenario_id: routeQuery.scenarioId, blocked_edge_ids: routeQuery.blocked,
    }, ctl.signal)
      .then((res) => {
        const next = { res, scenarioId: routeQuery.scenarioId, blocked: routeQuery.blocked }
        setPrevRoute(nextPrevious(routeRef.current ?? carriedRoute.current, next, routePoints, prevRouteRef.current))
        carriedRoute.current = null
        setRoute(next)
        markServerUp()
      })
      .catch((e: Error) => {
        if (ctl.signal.aborted) return
        pendingFit.current = false   // request lỗi: không để lần sau tự thu phóng bất ngờ (review #135)
        setRoute(null)
        setError(`Lỗi: ${e.message}`)
        checkServer()
      })
      .finally(() => !ctl.signal.aborted && setBusy(false))
    return () => {
      ctl.abort()
      setBusy(false)
    }
  }, [routeQuery, checkServer, markServerUp])

  useEffect(() => {
    if (!tourQuery) return
    const ctl = new AbortController()
    setBusy(true)
    setError(null)
    postTour({
      depot: { lat: tourQuery.depot.lat, lon: tourQuery.depot.lon },
      stops: tourQuery.stops.map(({ id, lat, lon }) => ({ id, lat, lon })),
      scenario_id: tourQuery.scenarioId,
      blocked_edge_ids: tourQuery.blocked,
      ...(tourQuery.keepOrder ? { keep_order: tourQuery.keepOrder } : {}),
      include_optimal: tourQuery.stops.length + 1 <= 11,   // Held–Karp tối đa 11 điểm kể cả kho
    }, ctl.signal)
      .then((res) => {
        const next = { res, scenarioId: tourQuery.scenarioId, blocked: tourQuery.blocked }
        setPrevTour(nextPrevious(tourRunRef.current ?? carriedTour.current, next, tourPoints, prevTourRef.current))
        carriedTour.current = null
        setTour(res)
        setTourScenario({ scenarioId: tourQuery.scenarioId, blocked: tourQuery.blocked })
        markServerUp()
        setTourMethod(res.chosen)
      })
      .catch((e: Error) => {
        if (ctl.signal.aborted) return
        pendingFit.current = false   // request lỗi: không để lần sau tự thu phóng bất ngờ (review #135)
        setTour(null)
        // API gọi điểm bằng id nội bộ ('p2', 'depot'); đổi sang tên người dùng thấy trên marker (QA-13).
        const names: Record<string, string> = Object.fromEntries(tourQuery.stops.map((s) => [s.id, s.label]))
        names.depot = 'kho'
        const msg = e.message.replace(/'([\w-]+)'/g, (m, id: string) => (id in names ? `"${names[id]}"` : m))
        setError(`Lỗi: ${msg}`)
        checkServer()
      })
      .finally(() => !ctl.signal.aborted && setBusy(false))
    return () => {
      ctl.abort()
      setBusy(false)
    }
  }, [tourQuery, checkServer, markServerUp])

  useEffect(() => {
    if (!showTrace || !routeQuery || mode !== 'route') {
      setTrace(null)
      return
    }
    setTrace(null)   // bỏ chấm của truy vấn cũ ngay, không để hiện lẫn tới khi trace mới về (review #139)
    const ctl = new AbortController()
    postRoute({
      source: latLon(routeQuery.source), target: latLon(routeQuery.target), algorithms: ['dijkstra', 'astar'],
      scenario_id: routeQuery.scenarioId, blocked_edge_ids: routeQuery.blocked, trace_limit: TRACE_LIMIT,
    }, ctl.signal)
      .then(setTrace)
      .catch(() => { if (!ctl.signal.aborted) setTrace(null) })   // lớp phụ: lỗi thì chỉ không vẽ chấm
    return () => ctl.abort()
  }, [showTrace, routeQuery, mode])

  // Viền vùng có dữ liệu: vẽ lại khi bản đồ được tạo lại (đổi bố cục) hoặc khi đọc xong /api/dataset.
  useEffect(() => {
    layersRef.current?.setDataArea(dataArea)
  }, [mapReady, dataArea])

  // Đóng/mở đoạn khi đang có kết quả thì tìm lại ngay với danh sách cạnh đóng mới.
  useEffect(() => {
    setRouteQuery((q) => (q && !sameIds(q.blocked, blocked) ? { ...q, blocked, n: q.n + 1 } : q))
  }, [blocked])

  // R1 C5: tour cũng vậy. Đóng thêm đoạn thì gửi kèm thứ tự đang xem lúc bấm (giữ thứ tự cũ); mở lại hết thì
  // lập lại tour ban đầu, không còn phương án giữ thứ tự cũ.
  useEffect(() => {
    setTourQuery((q) => {
      if (!q || sameIds(q.blocked, tourBlocked)) return q
      const keepOrder = tourBlocked.length ? (keepOrderOnClose.current ?? q.keepOrder) : undefined
      return { ...q, blocked: tourBlocked, keepOrder, n: q.n + 1 }
    })
  }, [tourBlocked])

  // --- Vẽ bản đồ từ state ---

  const closeSegment = useCallback((seg: RouteSegment) => {
    setNotice(null)
    setClosed((prev) => (prev.some((s) => s.edgeId === seg.edgeId) ? prev : [...prev, seg]))
  }, [])

  const closeTourSegment = useCallback((seg: RouteSegment) => {
    setNotice(null)
    keepOrderOnClose.current = shownTourOrder.current
    setTourClosed((prev) => (prev.some((s) => s.edgeId === seg.edgeId) ? prev : [...prev, seg]))
  }, [])

  useEffect(() => {
    const layers = layersRef.current
    if (!layers) return
    layers.setZones(scenario)
    const legend: LegendItem[] = []
    if (scenario.rules.length) legend.push({ kind: 'zone', label: 'Vùng cao điểm mô phỏng' })
    if (mode === 'route') {
      layers.setClosed(closedToDraw(route?.res.blocked_edges, closed))
      // Tuyến của lần trước (cùng điểm, khác kịch bản/cạnh đóng) vẽ mờ làm mốc, chỉ khi khác tuyến hiện tại.
      const before = prevRoute?.res.results.dijkstra
      const now = route?.res.results.dijkstra
      const moved = before?.status === 'ok' && (now?.status !== 'ok' || before.edge_ids?.join() !== now.edge_ids?.join())
      layers.setPrevious(route && moved ? before.geometry.coordinates : null)
      const d = route?.res.results.dijkstra
      const a = route?.res.results.astar
      if (d?.status === 'ok' && a?.status === 'ok' && d.edge_ids?.join() === a.edge_ids?.join()) {
        legend.unshift({ kind: 'same', label: 'Dijkstra và A* trùng tuyến' })
      } else {
        if (a?.status === 'ok') legend.unshift({ kind: 'astar', label: 'Tuyến A* (nét đứt)' })
        if (d?.status === 'ok') legend.unshift({ kind: 'dijkstra', label: 'Tuyến Dijkstra' })
      }
      if (closedToDraw(route?.res.blocked_edges, closed).length) legend.push({ kind: 'closed', label: 'Đoạn đang đóng' })
      if (route && moved) legend.push({ kind: 'previous', label: 'Tuyến lần trước' })
      if (trace) legend.push({ kind: 'trace', label: 'Node đã mở rộng: Dijkstra, A*' })
      layers.setTrace(trace?.results.dijkstra?.trace ?? null, trace?.results.astar?.trace ?? null)
      if (route) {
        layers.setSnapped(route.res)
        layers.drawRoutes(route.res, closeSegment)
        if (pendingFit.current) {
          pendingFit.current = false
          const { source: s, target: t } = route.res.snapped
          const line = route.res.results.dijkstra?.geometry.coordinates ?? []
          layers.fitTo([...toLatLngs([[s.lon, s.lat], [t.lon, t.lat]]), ...toLatLngs(line)])
        }
      } else {
        layers.clearRoutes()
        layers.setPoints(source, target)
      }
    } else {
      layers.setPrevious(null)
      layers.setTrace(null, null)
      layers.setClosed(closedToDraw(tour?.blocked_edges, tourClosed))
      const cand = tour && tourMethod ? tour.candidates[tourMethod] : undefined
      const broken = new Set(tour?.status === 'infeasible_under_model' ? unreachableGroups(tour.unreachable).map((g) => g.id) : [])
      layers.setTourPoints(depot, stops, cand?.stop_order, broken)
      if (cand) legend.unshift({ kind: 'tour', label: 'Tour đang xem' })
      if (closedToDraw(tour?.blocked_edges, tourClosed).length) legend.push({ kind: 'closed', label: 'Đoạn đang đóng' })
      if (broken.size) legend.push({ kind: 'broken', label: 'Điểm không đi được' })
      if (cand) layers.drawTour(cand, closeTourSegment)
      else layers.clearRoutes()
      if (tour && pendingFit.current) {
        pendingFit.current = false
        const pts = Object.values(tour.snapped).map((p): [number, number] => [p.lon, p.lat])
        layers.fitTo(toLatLngs([...pts, ...(cand?.geometry.coordinates ?? [])]), 160)
      }
    }
    layers.setLegend(legend)
  }, [mapReady, mode, scenario, route, prevRoute, trace, source, target, closed, closeSegment, tour, tourMethod, depot, stops,
    tourClosed, closeTourSegment])

  // --- Thao tác ---

  const resetRoute = () => {
    setRouteQuery(null)
    setRoute(null)
    setPrevRoute(null)
    carriedRoute.current = null
    setTarget(null)
    setClosed([])
    setCaseBlocked([])
    setError(null)
  }

  const resetTour = () => {
    setTourQuery(null)
    setTour(null)
    setTourScenario(null)
    setPrevTour(null)
    carriedTour.current = null
    setTourMethod(null)
    setError(null)
  }

  // Đang hiện kết quả thì cú bấm lên bản đồ không xoá gì (QA-1): một cú bấm trượt khỏi tuyến trong lúc demo
  // từng xoá cả tuyến lẫn các đoạn đã đóng. Muốn chọn lại thì bấm Xóa.
  const placePoint = (p: Pt) => {
    if (mode === 'route') {
      if (route) {
        setNotice('Đang hiện kết quả nên cú bấm lên bản đồ được bỏ qua. Bấm Xóa để chọn điểm mới.')
        return
      }
      setCaseId('')
      setNotice(null)
      setError(null)
      // Lần 1: điểm đi · lần 2: điểm đến · đã đủ hai điểm (chưa tìm) thì bắt đầu lại từ điểm đi.
      if (!source || target) {
        resetRoute()
        setSource(p)
      } else {
        setTarget(p)
      }
      return
    }
    if (tour) {
      setNotice('Đang hiện tour nên cú bấm lên bản đồ được bỏ qua. Bấm Xóa để lập tour mới.')
      return
    }
    setCaseId('')
    setNotice(null)
    // Kiểm giới hạn trước khi đổi gì (QA-12).
    if (depot && stops.length >= MAX_TOUR_STOPS) {
      setError(`Tối đa ${MAX_TOUR_STOPS} điểm giao.`)
      return
    }
    resetTour()
    if (!depot) setDepot({ ...latLon(p), id: 'depot', label: p.name ?? 'Kho' })
    else setStops([...stops, { ...latLon(p), id: `p${stops.length + 1}`, label: p.name ?? `Điểm ${stops.length + 1}` }])
  }
  const placePointRef = useRef(placePoint)
  placePointRef.current = placePoint

  // Kiểm điểm ngay lúc bấm (review 14/11 đợt 2, PM-7): điểm cách đường quá ngưỡng bị từ chối tại chỗ, kèm
  // khoảng cách, thay vì được đặt rồi làm hỏng cả tuyến/tour lúc gửi (trước đây lỗi 'p2' sau khi đặt 12 điểm).
  // Mỗi lần chỉ kiểm một cú bấm; không kiểm được (server lỗi) thì vẫn đặt, /api/route, /api/tour sẽ báo như cũ.
  const checking = useRef(false)
  // Tăng khi nạp case, đổi chế độ, Xóa hay Bỏ điểm cuối: kết quả kiểm về sau những thao tác đó bị bỏ, để điểm
  // không bị đặt vào case vừa nạp hay sang chế độ kia (góp ý #142).
  const clickGen = useRef(0)
  const onMapClick = (p: Pt) => {
    if ((mode === 'route' && route) || (mode === 'tour' && tour)) {
      placePoint(p)            // chỉ hiện gợi ý "Bấm Xóa", không đặt gì
      return
    }
    if (checking.current) return
    checking.current = true
    const gen = clickGen.current
    getSnap(p)
      .then((s) => {
        if (gen !== clickGen.current) return
        if (s.ok) placePointRef.current(p)
        else setError(`Điểm vừa bấm cách đường ${distanceText(s.snap_distance_m)}, quá ngưỡng ${s.max_m} m nên không được đặt. `
          + 'Hãy bấm gần đường hơn, trong viền vùng có dữ liệu.')
      })
      .catch(() => { if (gen === clickGen.current) placePointRef.current(p) })
      .finally(() => { checking.current = false })
  }

  // Bỏ điểm cuối (PM-7, U-2): bỏ điểm giao vừa thêm, hết điểm giao thì bỏ kho; không phải xoá cả tour làm lại.
  const removeLastPoint = () => {
    clickGen.current += 1
    setCaseId('')
    setNotice(null)
    resetTour()
    if (stops.length) setStops(stops.slice(0, -1))
    else setDepot(null)
  }

  const findRoute = () => {
    setNotice(null)
    if (!source || !target) return
    pendingFit.current = true
    setRouteQuery({ source, target, scenarioId, blocked, n: Date.now() })
  }

  const buildTour = () => {
    if (!depot) return
    pendingFit.current = true
    setTourQuery({ depot, stops, scenarioId, blocked: tourBlocked, n: Date.now() })
  }

  // Chưa tìm đường thì chỉ đổi chỗ hai điểm; trước đây nhánh này gọi resetRoute() nên mất điểm đến (QA-4).
  const swap = () => {
    if (!source || !target) return
    setSource(target)
    setTarget(source)
    // Đã gửi request (kể cả khi chưa về) thì phải tìm lại theo chiều mới; nếu chỉ đổi state, request cũ về sau
    // sẽ vẽ tuyến chiều cũ trong khi ô điểm đã đảo (review #134).
    if (routeQuery) setRouteQuery({ source: target, target: source, scenarioId, blocked, n: Date.now() })
  }

  const changeMode = (v: Mode) => {
    clickGen.current += 1
    setMode(v)
    setError(null)
    setNotice(null)
    // Ô case demo không giữ tên case của chế độ kia (UX-11).
    if (DEMO_CASES.find((c) => c.id === caseId)?.mode !== v) setCaseId('')
  }

  const clearAll = () => {
    clickGen.current += 1
    setNotice(null)
    setCaseId('')
    if (mode === 'route') {
      resetRoute()
      setSource(null)
    } else {
      resetTour()
      setDepot(null)
      setStops([])
      setTourClosed([])
      setTourCaseBlocked([])
    }
  }

  const reopenAll = () => {
    setNotice(null)
    if (mode === 'route') {
      setClosed([])
      setCaseBlocked([])
    } else {
      setTourClosed([])
      setTourCaseBlocked([])
    }
  }

  const changeScenario = (id: string) => {
    setScenarioId(id)
    setRouteQuery((q) => (q ? { ...q, scenarioId: id, n: q.n + 1 } : q))
    setTourQuery((q) => (q ? { ...q, scenarioId: id, n: q.n + 1 } : q))
  }

  const loadCase = (id: string) => {
    clickGen.current += 1
    const c = DEMO_CASES.find((x) => x.id === id)
    if (!c) return
    setCaseId(id)
    setError(null)
    setNotice(null)
    pendingFit.current = true
    // Lấy thẳng kịch bản của case, kể cả khi danh sách kịch bản chưa về (review #103); backend vẫn kiểm id (422).
    const sid = c.scenario_id ?? 'baseline'
    setScenarioId(sid)
    // Case đổi kịch bản chung, nên kết quả của chế độ kia (tính theo kịch bản cũ) phải bỏ; nếu không, ô
    // kịch bản và con số sẽ lệch nhau khi quay lại chế độ đó (QA-5).
    if (c.mode === 'route' && c.source && c.target) {
      const bl = c.blocked_edge_ids ?? []
      setTourQuery(null)
      setTour(null)
      setTourMethod(null)
      setMode('route')
      carriedRoute.current = routeRef.current
      setRoute(null)
      setPrevRoute(null)
      setClosed([])
      setCaseBlocked(bl)
      setSource(c.source)
      setTarget(c.target)
      setRouteQuery({ source: c.source, target: c.target, scenarioId: sid, blocked: bl, n: Date.now() })
    } else if (c.mode === 'tour' && c.depot && c.stops) {
      const d: TourPoint = { id: 'depot', label: c.depot.name, lat: c.depot.lat, lon: c.depot.lon }
      const st = c.stops.map((s, i) => ({ id: `p${i + 1}`, label: s.name, lat: s.lat, lon: s.lon }))
      const bl = c.blocked_edge_ids ?? []
      setRouteQuery(null)
      setRoute(null)
      setMode('tour')
      carriedTour.current = tourRunRef.current
      setTour(null)
      setPrevTour(null)
      setDepot(d)
      setStops(st)
      setTourClosed([])
      setTourCaseBlocked(bl)
      keepOrderOnClose.current = c.keep_order
      setTourQuery({ depot: d, stops: st, scenarioId: sid, blocked: bl, keepOrder: c.keep_order, n: Date.now() })
    }
  }

  const caseDisabled = datasetId !== null && datasetId !== DEMO_DATASET_ID
  const noPath = route && Object.values(route.res.results).some((r) => r?.status === 'no_path')
  const tourLabels = Object.fromEntries([...(depot ? [depot] : []), ...stops].map((p) => [p.id, p.label]))
  // Nhãn kịch bản cơ sở ghi "không đóng đường", nên phải nói rõ khi người dùng hoặc case đã đóng thêm cạnh.
  const runLabel = (r: { scenarioId: string; blocked: number[] }) => {
    const base = scenarios.find((s) => s.id === r.scenarioId)?.label ?? r.scenarioId
    return r.blocked.length > 0 ? `${base}; đóng thêm ${r.blocked.length} cạnh` : base
  }
  const routeScenarioLabel = route ? runLabel(route) : ''
  const tourScenarioLabel = tourScenario ? runLabel(tourScenario) : ''

  const hint = mode === 'route'
    ? (!source ? 'Bấm lên bản đồ để chọn điểm đi.'
      : !target ? 'Bấm để chọn điểm đến.'
        : route ? 'Bấm vào một đoạn trên tuyến để đóng đoạn đó. Bấm Xóa để chọn điểm mới.'
          : 'Bấm Tìm đường. Bấm lên bản đồ lần nữa để chọn lại từ đầu.')
    : (!depot ? 'Bấm lên bản đồ để đặt kho.'
      : tour?.status === 'ok' ? 'Bấm vào một đoạn trên tour để đóng đoạn đó; tour được lập lại. Bấm Xóa để lập tour mới.'
        : tour ? 'Bấm Mở lại tất cả để bỏ các đoạn đang đóng, hoặc Xóa để lập tour mới.'
          : `Bấm để thêm điểm giao (tối đa ${MAX_TOUR_STOPS}), rồi bấm Lập tour.`
            + (tourBlocked.length ? ' Các đoạn đang đóng vẫn giữ khi lập tour mới; bấm Mở lại tất cả để bỏ.' : ''))

  const controls = (
    <VStack gap={4}>
      <SegmentedControl label="Chế độ" value={mode} layout="fill" onChange={(v) => changeMode(v as Mode)}>
        <SegmentedControlItem value="route" label="Tìm đường" />
        <SegmentedControlItem value="tour" label="Tour" />
      </SegmentedControl>
      <Selector
        label="Case demo"
        placeholder="Chọn case minh họa"
        options={DEMO_CASES.map((c) => ({ value: c.id, label: c.label }))}
        value={caseId}
        onChange={loadCase}
        isDisabled={caseDisabled}
        disabledMessage={`Case demo dùng đồ thị ${DEMO_DATASET_ID}, server đang nạp ${datasetId}.`}
      />
      <Selector
        label="Kịch bản"
        options={scenarios.map((s) => ({ value: s.id, label: s.label }))}
        value={scenarioId}
        onChange={changeScenario}
      />
      {scenarioNote && <Text type="supporting">{scenarioNote}</Text>}
      <Text type="body">{hint}</Text>
      {/* Đặt điểm từ danh sách địa danh (đợt 3, C-b): như một cú bấm bản đồ tại địa danh đó, đi qua cùng
          bước kiểm; dùng được bằng bàn phím. Ô luôn về trống sau khi chọn để chọn tiếp được. */}
      <Selector
        label={mode === 'route' ? 'Đặt điểm từ địa danh' : 'Thêm kho / điểm giao từ địa danh'}
        placeholder="Chọn địa danh có tên"
        options={NAMED_PLACES.map((p) => ({ value: p.name, label: p.name }))}
        value=""
        onChange={(v) => {
          const place = NAMED_PLACES.find((p) => p.name === v)
          if (place) onMapClick(place)
        }}
        isDisabled={caseDisabled}
        disabledMessage={`Địa danh lấy toạ độ trên đồ thị ${DEMO_DATASET_ID}, server đang nạp ${datasetId}.`}
      />
      {mode === 'route' ? (
        <VStack gap={2}>
          <Text type="supporting">Điểm đi: {fmt(source)}</Text>
          <Text type="supporting">Điểm đến: {fmt(target)}</Text>
          <HStack gap={2}>
            <Button label="Tìm đường" variant="primary" isDisabled={!(source && target)} onClick={findRoute} />
            <Button label="Đảo chiều" isDisabled={!(source && target)} onClick={swap} />
            <Button label="Xóa" variant="ghost" onClick={clearAll} />
          </HStack>
          {blocked.length > 0 && (
            <HStack gap={2} vAlign="center" hAlign="between">
              <Text type="supporting">Đang đóng {blocked.length} cạnh</Text>
              <Button label="Mở lại tất cả" size="sm" onClick={reopenAll} />
            </HStack>
          )}
          <Switch label="Hiện node đã mở rộng" value={showTrace} onChange={setShowTrace}
            description="Chấm xanh: Dijkstra · chấm cam: A*. Lấy bằng một lần tìm riêng, không tính vào thời gian ở bảng." />
          {showTrace && trace && <Text type="supporting">{traceLegend(trace)}</Text>}
        </VStack>
      ) : (
        <VStack gap={2}>
          <Text type="supporting">
            {!depot ? 'Chưa đặt kho' : depot.label === 'Kho' ? 'Đã đặt kho' : `Kho: ${depot.label}`} · {stops.length} điểm giao
          </Text>
          <HStack gap={2}>
            <Button label="Lập tour" variant="primary" isDisabled={!depot || stops.length === 0} onClick={buildTour} />
            <Button label="Bỏ điểm cuối" isDisabled={!depot} onClick={removeLastPoint} />
            <Button label="Xóa" variant="ghost" onClick={clearAll} />
          </HStack>
          {tourBlocked.length > 0 && (
            <HStack gap={2} vAlign="center" hAlign="between">
              <Text type="supporting">Đang đóng {tourBlocked.length} cạnh</Text>
              <Button label="Mở lại tất cả" size="sm" onClick={reopenAll} />
            </HStack>
          )}
        </VStack>
      )}
      {busy && <Spinner label="Đang tính…" />}
      {notice && <Banner status="info" title={notice} />}
      {error && <Banner status="error" title={error} />}
      {mode === 'route' && noPath && (
        <Banner status="info" title="Không có đường đi giữa hai điểm này trong kịch bản hiện tại." />
      )}
    </VStack>
  )

  const results = mode === 'route'
    ? (route ? <RouteResults res={route.res} scenarioLabel={routeScenarioLabel}
      previous={prevRoute ? { res: prevRoute.res, label: runLabel(prevRoute) } : null} /> : <Text type="supporting">Chưa có kết quả.</Text>)
    : (tour ? <TourResults res={tour} labels={tourLabels} selected={tourMethod} onSelect={setTourMethod} scenarioLabel={tourScenarioLabel}
      previous={prevTour ? { res: prevTour.res, label: runLabel(prevTour) } : null} />
      : <Text type="supporting">Chưa có kết quả.</Text>)

  const resultsBlock = (
    <VStack gap={3}>
      <Heading level={2}>Kết quả đo được</Heading>
      {results}
    </VStack>
  )
  const map = <MapView onReady={onMapReady} onClick={onMapClick} />
  const header = (
    <LayoutHeader hasDivider>
      <HStack gap={3} vAlign="center" hAlign="between">
        <HStack gap={2} vAlign="center">
          <Heading level={1}>SaiGo</Heading>
          {!narrow && <Text type="supporting">Lập kế hoạch lộ trình giao hàng</Text>}
        </HStack>
        <Badge variant={server.ok === null ? 'neutral' : server.ok ? 'success' : 'error'}
          label={narrow && server.ok ? 'Sẵn sàng' : server.text} />
      </HStack>
    </LayoutHeader>
  )

  // Bố cục theo độ rộng (review 14/11 đợt 2, FE-1/UX-6/QA-10): trước đây hai cột cố định 320 + 380 px, nên máy
  // chiếu 1024 px chỉ còn ~324 px cho bản đồ và điện thoại 390 px thì bản đồ rộng 0.
  if (narrow) {
    // < 768 px: bản đồ ở trên (55% chiều cao), điều khiển và kết quả xếp dọc bên dưới, cả trang cuộn.
    return (
      <AppShell height="fill">
        <Layout
          header={header}
          content={
            <LayoutContent padding={0} isScrollable label="Ứng dụng">
              <VStack gap={0}>
                <VStack height="55dvh">{map}</VStack>
                <VStack gap={6} padding={4}>
                  {controls}
                  {resultsBlock}
                </VStack>
              </VStack>
            </LayoutContent>
          }
        />
      </AppShell>
    )
  }
  return (
    <AppShell height="fill">
      <Layout
        header={header}
        start={
          // 768–1365 px (máy chiếu 1024/1280): kết quả gộp xuống dưới điều khiển ở cột trái, bỏ cột phải.
          <LayoutPanel width={medium ? 360 : 300} hasDivider padding={4} label="Bảng điều khiển">
            {medium ? <VStack gap={6}>{controls}{resultsBlock}</VStack> : controls}
          </LayoutPanel>
        }
        content={
          <LayoutContent padding={0} isScrollable={false} label="Bản đồ">
            {map}
          </LayoutContent>
        }
        end={medium ? undefined : (
          <LayoutPanel width={360} hasDivider padding={4} label="Kết quả đo được">{resultsBlock}</LayoutPanel>
        )}
      />
    </AppShell>
  )
}
