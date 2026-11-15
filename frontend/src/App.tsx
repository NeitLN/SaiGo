// Giao diện SaiGo (T56): bố cục 3 cột theo DEMO mục 1 — điều khiển / bản đồ / kết quả đo được.
// Chế độ "Tìm đường hai điểm" (T14, T52, T53, đóng đoạn đường T54) và "Tour" (T73).
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AppShell } from '@astryxdesign/core/AppShell'
import { Banner } from '@astryxdesign/core/Banner'
import { Button } from '@astryxdesign/core/Button'
import { Divider } from '@astryxdesign/core/Divider'
import { EmptyState } from '@astryxdesign/core/EmptyState'
import { Heading } from '@astryxdesign/core/Heading'
import { HStack } from '@astryxdesign/core/HStack'
import { Layout, LayoutContent, LayoutHeader, LayoutPanel } from '@astryxdesign/core/Layout'
import { SegmentedControl, SegmentedControlItem } from '@astryxdesign/core/SegmentedControl'
import { Selector } from '@astryxdesign/core/Selector'
import { Spinner } from '@astryxdesign/core/Spinner'
import { StackItem } from '@astryxdesign/core/Stack'
import { StatusDot } from '@astryxdesign/core/StatusDot'
import { Switch } from '@astryxdesign/core/Switch'
import { Text } from '@astryxdesign/core/Text'
import { Tooltip } from '@astryxdesign/core/Tooltip'
import { Theme } from '@astryxdesign/core/theme'
import { VStack } from '@astryxdesign/core/VStack'
import { useAnnounce, useMediaQuery } from '@astryxdesign/core/hooks'
import {
  BASELINE, MAX_TOUR_STOPS, TOUR_METHOD_LABEL, getSnap, postRoute, postTour,
  type BlockedEdge, type LatLon, type RouteResponse, type TourMethod, type TourResponse,
} from './api'
import { DEMO_CASES, DEMO_DATASET_ID, NAMED_PLACES } from './cases'
import { costDelta, deltaText } from './compare'
import { Grid } from '@astryxdesign/core/Grid'
import Kpi, { km, metersRaw, minutes, minutesText, secondsRaw } from './Kpi'
import { routeSegments, segmentLength, toLatLngs, zoneLegend, type LegendItem, type MapLayers, type RouteSegment, type TourPoint } from './layers'
import MapView from './MapView'
import RouteResults from './RouteResults'
import TourResults from './TourResults'
import { unreachableGroups } from './tourIssues'
import {
  TRACE_LIMIT, addTourPoint, blockedIds, distanceText, fmt, latLon, nextPrevious, nextRoutePoint, removeLastTourPoint,
  closedMore, renameIds, routeAnnouncement, routePoints, runLabel as scenarioRunLabel, sameIdList, segmentLabels, tourAnnouncement, tourPoints, traceLegend, type Mode, type Pt,
  type Run,
} from './appLogic'
import { useServerStatus } from './useServerStatus'
import { Logo } from './Logo'
import { themes, defaultThemeSlug } from './astryx-themes'

// Mỗi lần gửi request là một query mới (n tăng); effect hủy request cũ nên chỉ kết quả mới nhất được hiện.
interface RouteQuery { source: LatLon; target: LatLon; scenarioId: string; blocked: number[]; n: number }
// keepOrder (R1): thứ tự điểm giao trước khi đóng đường, để API trả thêm phương án "Giữ thứ tự cũ".
interface TourQuery { depot: TourPoint; stops: TourPoint[]; scenarioId: string; blocked: number[]; keepOrder?: string[]; n: number }

// Đoạn đóng để vẽ: cạnh đang đóng đã có hình học từ một response trước (gồm cả cạnh đóng sẵn của case, QA-3) cộng
// các đoạn vừa bấm mà response chưa có, để nét đỏ hiện ngay khi bấm, không chờ request về (review #135). Hình học
// nhớ qua các response (test lại 15/11, T-4): trước đây Bỏ điểm cuối hay request lỗi làm mất nét đỏ của cạnh đóng
// sẵn trong khi cạnh đó vẫn được gửi lên API.
const closedToDraw = (ids: number[], geom: Map<number, BlockedEdge>, clicked: RouteSegment[]): RouteSegment[] => {
  const drawn = ids.flatMap((id) => {
    const b = geom.get(id)
    return b ? [{ edgeId: id, twinId: null, latlngs: toLatLngs(b.geometry) }] : []
  })
  const known = new Set(drawn.map((s) => s.edgeId))
  return [...drawn, ...clicked.filter((s) => !known.has(s.edgeId))]
}

// Kiểm điểm quá thời gian này thì coi như không kiểm được và vẫn đặt (test lại 15/11, C-2).
const SNAP_TIMEOUT_MS = 4000
// Khay phân tích dưới bản đồ khi mở (đợt UI "Bàn điều phối"): đủ cho thanh node hoặc bốn dòng phương án ở 1280 × 800.
const TRAY_HEIGHT = 220

export default function App() {
  const narrow = useMediaQuery('(max-width: 767px)')
  // Ba cột chỉ từ 1440 px: máy chiếu 1280 × 800 dùng bố cục hai cột, bản đồ 920 px thay vì 620 (góp ý #141); ở
  // 1366 × 768 ba cột chỉ còn 706 px cho bản đồ và cắt chữ ô kịch bản (test lại 15/11, A-7), nên cũng hai cột.
  const medium = useMediaQuery('(max-width: 1439px)')
  const layersRef = useRef<MapLayers | null>(null)
  const [trayOpen, setTrayOpen] = useState(true)
  // Thu/mở khay đổi chiều cao bản đồ (MapView tự invalidateSize qua ResizeObserver); thu phóng lại cho vừa kết quả.
  const toggleTray = () => {
    setTrayOpen((o) => !o)
    layersRef.current?.refitAfterResize()
  }
  const [mapReady, setMapReady] = useState(0)
  const onMapReady = useCallback((l: MapLayers) => {
    layersRef.current = l
    // Bản đồ được tạo lại khi đổi bố cục (breakpoint): thu phóng lại cho vừa kết quả đang hiện.
    pendingFit.current = true
    setMapReady((n) => n + 1)
  }, [])

  const { server, datasetId, dataArea, scenarios, scenarioNote, checkServer, markServerUp } = useServerStatus()
  const [scenarioId, setScenarioId] = useState('baseline')
  const [mode, setMode] = useState<Mode>('route')
  // Ô Case demo nhớ riêng theo chế độ (test lại 15/11, R-8/T-7): trước đây đổi chế độ rồi quay lại thì ô trống dù
  // kết quả của case vẫn đang hiện. setCaseId đổi ô của chế độ đang xem.
  const [caseIds, setCaseIds] = useState<Record<Mode, string>>({ route: '', tour: '' })
  const caseId = caseIds[mode]
  const setCaseId = (id: string) => setCaseIds((s) => ({ ...s, [modeRef.current]: id }))
  // Bận và lỗi tách theo chế độ (review 14/11 đợt 3, QA-11): đổi kịch bản chạy lại query của cả hai chế độ, nên
  // dùng chung một cờ thì spinner tắt sớm và lỗi của chế độ đang ẩn hiện ở chế độ đang xem.
  const [busyRoute, setBusyRoute] = useState(false)
  const [busyTour, setBusyTour] = useState(false)
  const [errorState, setErrorState] = useState<{ mode: Mode; text: string } | null>(null)
  const modeRef = useRef<Mode>('route')
  /** Lỗi của thao tác người dùng vừa làm: gắn với chế độ đang xem; null thì xoá mọi lỗi. */
  const setError = useCallback((text: string | null) => setErrorState(text ? { mode: modeRef.current, text } : null), [])
  modeRef.current = mode
  const clearErrorOf = (m: Mode) => setErrorState((s) => (s?.mode === m ? null : s))
  // Đọc kết quả cho người dùng trình đọc màn hình (FE-3): Banner của Astryx không có live region.
  const announce = useAnnounce()
  const announceRef = useRef(announce)
  announceRef.current = announce
  // Tạo sẵn vùng đọc (rỗng) ngay khi mở trang: vùng live chèn vào cùng lúc với nội dung thì trình đọc màn hình thường bỏ
  // qua câu đầu tiên (test lại 15/11, A-9). Câu rỗng chỉ xoá trạng thái, không đọc gì.
  useEffect(() => { announceRef.current('') }, [])
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
  // Phần mở rộng (D17, đợt 3 phương án E-b): tắt mặc định để 4 phút demo không lẫn thứ ngoài proposal; bật khi
  // hỏi đáp. Bật/tắt thì tìm lại với cùng tham số (đọc qua ref để không đưa vào deps của effect gọi API).
  const [showExt, setShowExt] = useState(false)
  const showExtRef = useRef(showExt)
  showExtRef.current = showExt

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
  // Đang xem thẻ Held–Karp (chỉ để đối chứng, không phải tour đang chạy) thì "thứ tự cũ" là của phương án được chọn
  // (test lại 15/11: trước đây đóng đường lúc xem thẻ tối ưu làm "Giữ thứ tự cũ" rẻ hơn hẳn và nhận badge "Rẻ nhất",
  // dù thứ tự đó chưa từng được chọn).
  const keepFrom = tourMethod === 'optimal' ? tour?.chosen : tourMethod
  shownTourOrder.current = tour && keepFrom ? tour.candidates[keepFrom]?.stop_order : undefined
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
  // Hình học các cạnh đóng đã gặp trong response (id cạnh → BlockedEdge); xem closedToDraw.
  const edgeGeom = useRef(new Map<number, BlockedEdge>())
  const rememberEdges = (edges: BlockedEdge[] | undefined) => edges?.forEach((b) => edgeGeom.current.set(b.edge_id, b))

  // --- Gọi API ---

  useEffect(() => {
    if (!routeQuery) return
    const ctl = new AbortController()
    setBusyRoute(true)
    clearErrorOf('route')
    postRoute({
      source: latLon(routeQuery.source), target: latLon(routeQuery.target),
      algorithms: showExtRef.current ? ['dijkstra', 'astar', 'alt', 'bidijkstra'] : ['dijkstra', 'astar'],
      scenario_id: routeQuery.scenarioId, blocked_edge_ids: routeQuery.blocked,
    }, ctl.signal)
      .then((res) => {
        announceRef.current(routeAnnouncement(res))
        rememberEdges(res.blocked_edges)
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
        setErrorState({ mode: 'route', text: `Lỗi: ${e.message}` })
        checkServer()
      })
      .finally(() => !ctl.signal.aborted && setBusyRoute(false))
    return () => {
      ctl.abort()
      setBusyRoute(false)
    }
  }, [routeQuery, checkServer, markServerUp])

  useEffect(() => {
    if (!tourQuery) return
    const ctl = new AbortController()
    setBusyTour(true)
    clearErrorOf('tour')
    postTour({
      depot: { lat: tourQuery.depot.lat, lon: tourQuery.depot.lon },
      stops: tourQuery.stops.map(({ id, lat, lon }) => ({ id, lat, lon })),
      scenario_id: tourQuery.scenarioId,
      blocked_edge_ids: tourQuery.blocked,
      ...(tourQuery.keepOrder ? { keep_order: tourQuery.keepOrder } : {}),
      include_optimal: tourQuery.stops.length + 1 <= 11,   // Held–Karp tối đa 11 điểm kể cả kho
      ...(showExtRef.current ? { include_or_opt: true } : {}),
    }, ctl.signal)
      .then((res) => {
        announceRef.current(tourAnnouncement(res))
        rememberEdges(res.blocked_edges)
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
        // API gọi điểm bằng id nội bộ ('p2', 'depot'); đổi sang tên trên marker (QA-13).
        const msg = renameIds(e.message, tourQuery.stops)
        setErrorState({ mode: 'tour', text: `Lỗi: ${msg}` })
        checkServer()
      })
      .finally(() => !ctl.signal.aborted && setBusyTour(false))
    return () => {
      ctl.abort()
      setBusyTour(false)
    }
  }, [tourQuery, checkServer, markServerUp])

  // Trace chỉ phụ thuộc hai điểm, kịch bản và cạnh đóng: bật/tắt Phần mở rộng hay bấm lại Tìm đường với cùng tham số
  // không gửi lại request trace (test lại 15/11; trước đây mỗi lần đều gửi lại và nháy lớp chấm).
  const traceKey = routeQuery
    ? JSON.stringify([latLon(routeQuery.source), latLon(routeQuery.target), routeQuery.scenarioId, routeQuery.blocked])
    : null
  useEffect(() => {
    if (!showTrace || !traceKey || mode !== 'route') {
      setTrace(null)
      return
    }
    setTrace(null)   // bỏ chấm của truy vấn cũ ngay, không để hiện lẫn tới khi trace mới về (review #139)
    const [source, target, scenarioId, blocked] = JSON.parse(traceKey) as [LatLon, LatLon, string, number[]]
    const ctl = new AbortController()
    postRoute({
      source, target, algorithms: ['dijkstra', 'astar'],
      scenario_id: scenarioId, blocked_edge_ids: blocked, trace_limit: TRACE_LIMIT,
    }, ctl.signal)
      .then(setTrace)
      .catch(() => { if (!ctl.signal.aborted) setTrace(null) })   // lớp phụ: lỗi thì chỉ không vẽ chấm
    return () => ctl.abort()
  }, [showTrace, traceKey, mode])

  const toggleExt = (on: boolean) => {
    setShowExt(on)
    showExtRef.current = on
    setRouteQuery((q) => (q ? { ...q, n: q.n + 1 } : q))
    setTourQuery((q) => (q ? { ...q, n: q.n + 1 } : q))
  }

  // Viền vùng có dữ liệu: vẽ lại khi bản đồ được tạo lại (đổi bố cục) hoặc khi đọc xong /api/dataset.
  useEffect(() => {
    layersRef.current?.setDataArea(dataArea)
  }, [mapReady, dataArea])

  // Đóng/mở đoạn khi đang có kết quả thì tìm lại ngay với danh sách cạnh đóng mới.
  useEffect(() => {
    setRouteQuery((q) => (q && !sameIdList(q.blocked, blocked) ? { ...q, blocked, n: q.n + 1 } : q))
  }, [blocked])

  // R1 C5: tour cũng vậy. Đóng thêm đoạn thì gửi kèm thứ tự đang xem lúc bấm (giữ thứ tự cũ); mở lại hết thì
  // lập lại tour ban đầu, không còn phương án giữ thứ tự cũ.
  useEffect(() => {
    setTourQuery((q) => {
      if (!q || sameIdList(q.blocked, tourBlocked)) return q
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
    // Vùng ùn tắc theo kịch bản của kết quả đang hiện (test lại 15/11, C-5): trong lúc chờ request của kịch bản mới,
    // bản đồ và bảng vẫn khớp nhau; chưa có kết quả thì theo kịch bản đang chọn.
    const shownId = mode === 'route' ? route?.scenarioId : tourScenario?.scenarioId
    const zones = scenarios.find((s) => s.id === shownId) ?? scenario
    layers.setZones(zones)
    const legend: LegendItem[] = []
    // Nhãn trên bản đồ chỉ ghi "×2"; hệ số và loại đường đầy đủ ghi ở chú giải (đợt UI 15/11).
    if (zones.rules.length) legend.push({ kind: 'zone', label: zoneLegend(zones) })
    if (mode === 'route') {
      layers.setClosed(closedToDraw(blocked, edgeGeom.current, closed))
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
      if (source) legend.push({ kind: 'point', label: target ? 'Điểm đi, điểm đến' : 'Điểm đi' })
      if (closedToDraw(blocked, edgeGeom.current, closed).length) legend.push({ kind: 'closed', label: 'Đoạn đang đóng' })
      if (route && moved) legend.push({ kind: 'previous', label: 'Tuyến lần trước' })
      // Chỉ vẽ node đã mở rộng khi có kết quả: request chính lỗi mà trace về được thì không vẽ (test lại 15/11, C-4).
      const shownTrace = route ? trace : null
      if (shownTrace) legend.push({ kind: 'trace', label: 'Node đã mở rộng: Dijkstra, A*' })
      layers.setTrace(shownTrace?.results.dijkstra?.trace ?? null, shownTrace?.results.astar?.trace ?? null)
      if (route) {
        layers.setSnapped(route.res, { source: source?.name, target: target?.name })
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
      layers.setClosed(closedToDraw(tourBlocked, edgeGeom.current, tourClosed))
      const cand = tour && tourMethod ? tour.candidates[tourMethod] : undefined
      const broken = new Set(tour?.status === 'infeasible_under_model' ? unreachableGroups(tour.unreachable).map((g) => g.id) : [])
      layers.setTourPoints(depot, stops, cand?.stop_order, broken)
      if (cand) legend.unshift({ kind: 'tour', label: 'Tour đang xem' })
      if (depot) legend.push({ kind: 'depot', label: 'Kho' })
      if (stops.length) legend.push({ kind: 'stop', label: cand ? 'Điểm giao, số là thứ tự đi' : 'Điểm giao' })
      if (closedToDraw(tourBlocked, edgeGeom.current, tourClosed).length) legend.push({ kind: 'closed', label: 'Đoạn đang đóng' })
      if (broken.size) legend.push({ kind: 'broken', label: 'Điểm không đi được' })
      if (cand) layers.drawTour(cand, closeTourSegment)
      else layers.clearRoutes()
      if (tour && pendingFit.current) {
        pendingFit.current = false
        // Tour không khả thi: thu phóng vào điểm hỏng và đoạn đang đóng (test lại 15/11, T-3/D-4: ở mức vừa cả tour,
        // cạnh đóng 24 m sát Nhà hát chỉ còn vài pixel nằm dưới marker).
        const pts = Object.entries(tour.snapped)
          .filter(([id]) => !broken.size || broken.has(id))
          .map(([, p]): [number, number] => [p.lon, p.lat])
        const extra = broken.size
          ? closedToDraw(tourBlocked, edgeGeom.current, tourClosed).flatMap((s) => s.latlngs)
          : toLatLngs(cand?.geometry.coordinates ?? [])
        layers.fitTo([...toLatLngs(pts), ...extra], 160)
      }
    }
    layers.setLegend(legend)
  }, [mapReady, mode, scenario, scenarios, tourScenario, route, prevRoute, trace, source, target, closed, blocked, closeSegment, tour, tourMethod, depot,
    stops, tourClosed, tourBlocked, closeTourSegment])

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
        setNotice('Đang hiện kết quả nên điểm mới không được đặt. Bấm Xóa để chọn điểm mới.')
        return
      }
      const next = nextRoutePoint(source, target, p)
      if (next.kind === 'error') {
        setError(next.text)
        return
      }
      setCaseId('')
      setNotice(null)
      setError(null)
      if (next.restart) resetRoute()
      setSource(next.source)
      setTarget(next.target)
      // Đọc cho trình đọc màn hình (test lại 15/11, A-6): trước đây đặt điểm không có thông báo nào.
      announceRef.current(next.target ? `Đã đặt điểm đến: ${fmt(next.target)}.` : `Đã đặt điểm đi: ${fmt(next.source)}.`)
      return
    }
    if (tour) {
      setNotice('Đang hiện tour nên điểm mới không được thêm. Bấm Xóa để lập tour mới.')
      return
    }
    setCaseId('')
    setNotice(null)
    // Giới hạn số điểm (QA-12) và chặn trùng (góp ý #145) kiểm trước khi đổi gì; xem addTourPoint.
    const added = addTourPoint(depot, stops, p, MAX_TOUR_STOPS)
    if (added.kind === 'error') {
      setError(added.text)
      return
    }
    resetTour()
    if (added.kind === 'depot') {
      setDepot(added.depot)
      announceRef.current(`Đã đặt kho: ${added.depot.label}.`)
    } else {
      setStops(added.stops)
      const last = added.stops[added.stops.length - 1]
      announceRef.current(`Đã thêm điểm giao ${added.stops.length}: ${last.label}.`)
    }
  }
  const placePointRef = useRef(placePoint)
  placePointRef.current = placePoint

  // Kiểm điểm ngay lúc bấm (review 14/11 đợt 2, PM-7): điểm cách đường quá ngưỡng bị từ chối tại chỗ, kèm
  // khoảng cách, thay vì được đặt rồi làm hỏng cả tuyến/tour lúc gửi (trước đây lỗi 'p2' sau khi đặt 12 điểm).
  // Không kiểm được (server lỗi, hoặc quá SNAP_TIMEOUT_MS) thì vẫn đặt, /api/route, /api/tour sẽ báo như cũ.
  // Các cú bấm kiểm lần lượt theo hàng đợi (test lại 15/11, C-2/R-6: trước đây cú bấm trong lúc đang kiểm bị bỏ
  // lặng lẽ, và một lần kiểm treo khoá mọi cách đặt điểm tới khi tải lại trang).
  const snapQueue = useRef<Promise<void>>(Promise.resolve())
  const snapCtl = useRef<AbortController | null>(null)
  const [checkingPoints, setCheckingPoints] = useState(0)
  // Tăng khi nạp case, đổi chế độ, Xóa, Bỏ điểm cuối, Tìm đường, Lập tour hay Đảo chiều: kết quả kiểm về sau những
  // thao tác đó bị bỏ, để điểm không bị đặt vào case vừa nạp hay sang chế độ kia (góp ý #142), và không xoá
  // request vừa gửi (test lại 15/11, C-1: kiểm về sau Tìm đường từng bắt đầu lại từ điểm đi và huỷ lặng lẽ request).
  const clickGen = useRef(0)
  const dropPendingClicks = () => {
    clickGen.current += 1
    snapCtl.current?.abort()
  }
  const onMapClick = (p: Pt) => {
    if ((mode === 'route' && route) || (mode === 'tour' && tour)) {
      placePoint(p)            // chỉ hiện gợi ý "Bấm Xóa", không đặt gì
      return
    }
    const gen = clickGen.current
    setCheckingPoints((n) => n + 1)
    snapQueue.current = snapQueue.current.then(async () => {
      const ctl = new AbortController()
      const timer = window.setTimeout(() => ctl.abort(), SNAP_TIMEOUT_MS)
      snapCtl.current = ctl
      try {
        if (gen !== clickGen.current) return
        const s = await getSnap(p, ctl.signal)
        if (gen !== clickGen.current) return
        // Đặt đúng toạ độ node vừa snap (T-5, R-8): marker nằm trên đường, ô điểm hiện toạ độ thật dùng để tìm, và
        // hai cú bấm vào cùng node bị chặn trùng ngay. Tên địa danh (nếu có) giữ nguyên.
        if (s.ok) placePointRef.current({ ...p, lat: s.lat, lon: s.lon })
        else setError(`Điểm vừa bấm cách đường đi được gần nhất ${distanceText(s.snap_distance_m)}, quá ngưỡng ${s.max_m} m nên không được đặt. `
          + 'Hãy bấm gần đường hơn, trong viền vùng có dữ liệu.')
      } catch {
        if (gen === clickGen.current) placePointRef.current(p)
      } finally {
        window.clearTimeout(timer)
        setCheckingPoints((n) => n - 1)
      }
    })
  }

  // Bỏ điểm cuối (PM-7, U-2): bỏ điểm giao vừa thêm, hết điểm giao thì bỏ kho; không phải xoá cả tour làm lại.
  const removeLastPoint = () => {
    dropPendingClicks()
    setCaseId('')
    setNotice(null)
    resetTour()
    const left = removeLastTourPoint(depot, stops)
    setDepot(left.depot)
    setStops(left.stops)
  }

  const findRoute = () => {
    setNotice(null)
    if (!source || !target) return
    dropPendingClicks()
    pendingFit.current = true
    setRouteQuery({ source, target, scenarioId, blocked, n: Date.now() })
  }

  const buildTour = () => {
    if (!depot) return
    dropPendingClicks()
    pendingFit.current = true
    setTourQuery({ depot, stops, scenarioId, blocked: tourBlocked, n: Date.now() })
  }

  // Chưa tìm đường thì chỉ đổi chỗ hai điểm; trước đây nhánh này gọi resetRoute() nên mất điểm đến (QA-4).
  const swap = () => {
    if (!source || !target) return
    dropPendingClicks()
    setNotice(null)      // gợi ý "Đang hiện kết quả…" của lần trước không còn đúng (R-5)
    setCaseId('')        // đã đảo thì không còn là case vừa chọn (C-5)
    setSource(target)
    setTarget(source)
    // Đã gửi request (kể cả khi chưa về) thì phải tìm lại theo chiều mới; nếu chỉ đổi state, request cũ về sau
    // sẽ vẽ tuyến chiều cũ trong khi ô điểm đã đảo (review #134).
    if (routeQuery) setRouteQuery({ source: target, target: source, scenarioId, blocked, n: Date.now() })
  }

  const changeMode = (v: Mode) => {
    dropPendingClicks()
    setMode(v)
    // Không xoá lỗi: lỗi đã gắn theo chế độ, chỉ hiện ở chế độ sinh ra nó, quay lại vẫn thấy (góp ý #147).
    setNotice(null)
  }

  const clearAll = () => {
    dropPendingClicks()
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
    setCaseId('')        // bỏ cạnh đóng của case thì ô không còn ghi tên case đó (T-7)
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
    dropPendingClicks()
    const c = DEMO_CASES.find((x) => x.id === id)
    if (!c) return
    // Nạp case bỏ kết quả của chế độ kia (xem dưới), nên ô case của chế độ đó cũng về trống.
    setCaseIds({ route: c.mode === 'route' ? id : '', tour: c.mode === 'tour' ? id : '' })
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
      // Nạp liên tiếp khi case trước chưa về (C-5): giữ mốc cũ thay vì ghi đè bằng null.
      carriedRoute.current = routeRef.current ?? carriedRoute.current
      carriedTour.current = tourRunRef.current ?? carriedTour.current
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
      carriedTour.current = tourRunRef.current ?? carriedTour.current
      carriedRoute.current = routeRef.current ?? carriedRoute.current
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

  // Đang kiểm điểm vừa chọn thì chưa cho Tìm đường / Lập tour / Đảo chiều (góp ý #150): bấm lúc đó sẽ bỏ điểm đang
  // kiểm, nên tour hay tuyến thiếu điểm người dùng vừa thêm.
  const checking = checkingPoints > 0
  const caseDisabled = datasetId !== null && datasetId !== DEMO_DATASET_ID
  const noPath = route && Object.values(route.res.results).some((r) => r?.status === 'no_path')
  const tourLabels = Object.fromEntries([...(depot ? [depot] : []), ...stops].map((p) => [p.id, p.label]))
  // Nhãn kịch bản cơ sở ghi "không đóng đường", nên phải nói rõ khi người dùng hoặc case đã đóng thêm cạnh.
  const runLabel = (r: { scenarioId: string; blocked: number[] }) =>
    scenarioRunLabel(scenarios.find((s) => s.id === r.scenarioId)?.label ?? r.scenarioId, r.blocked.length)
  const routeScenarioLabel = route ? runLabel(route) : ''
  const tourScenarioLabel = tourScenario ? runLabel(tourScenario) : ''

  // Đóng đoạn bằng bàn phím (test lại 15/11, A-1): vùng bấm trên bản đồ chỉ dùng được bằng chuột, nên liệt kê các
  // đoạn của tuyến / tour đang xem trong một ô chọn; chọn một đoạn như bấm vào nó trên bản đồ.
  const shownCand = tour && tourMethod ? tour.candidates[tourMethod] : undefined
  const keySegs = mode === 'route'
    ? (route && !noPath && route.res.results.dijkstra ? routeSegments(route.res.results.dijkstra) : [])
    : (tour?.status === 'ok' && shownCand ? routeSegments(shownCand) : [])
  const keyLabels = segmentLabels(keySegs.map(segmentLength), mode === 'route' ? 'điểm đi' : 'kho')
  const closeByKey = (v: string) => {
    const seg = keySegs[Number(v)]
    if (seg) (mode === 'route' ? closeSegment : closeTourSegment)(seg)
  }

  // Tóm tắt kết quả ở đầu cột trái khi không có cột kết quả riêng (< 1440 px; test lại 15/11, D-2): ở máy chiếu
  // 1280 px, bảng kết quả nằm dưới điều khiển nên người xem không thấy số nếu không cuộn.
  const routeCost = (r: RouteResponse) => (r.results.dijkstra?.status === 'ok' ? r.results.dijkstra.cost_s : null)
  const tourCost = (r: TourResponse) => (r.status === 'ok' && r.chosen ? r.candidates[r.chosen]?.cost_s ?? null : null)
  const summary = mode === 'route'
    ? (route ? routeAnnouncement(route.res)
      + (prevRoute ? ` So với lần trước: ${deltaText(costDelta(routeCost(prevRoute.res), routeCost(route.res)))}.` : '') : null)
    : (tour ? tourAnnouncement(tour)
      + (prevTour ? ` So với lần trước: ${deltaText(costDelta(tourCost(prevTour.res), tourCost(tour)), 'tour')}.` : '') : null)

  const viewedTour = tour?.status === 'ok' && tourMethod ? tour.candidates[tourMethod] : undefined
  const summaryKpi = mode === 'route'
    ? (route && routeCost(route.res) !== null
      ? {
          timeNote: 'theo điều kiện giao thông',
          cost: routeCost(route.res)!, dist: route.res.results.dijkstra?.distance_m ?? 0,
          delta: prevRoute ? deltaText(costDelta(routeCost(prevRoute.res), routeCost(route.res))) : null,
        }
      : null)
    : (viewedTour
      ? {
          timeNote: TOUR_METHOD_LABEL[tourMethod!],
          cost: viewedTour.cost_s, dist: viewedTour.distance_m,
          delta: prevTour ? deltaText(costDelta(tourCost(prevTour.res), tourCost(tour!)), 'tour') : null,
        }
      : null)

  const hint = mode === 'route'
    ? (!source ? 'Bấm lên bản đồ để chọn điểm đi.'
      : !target ? 'Bấm để chọn điểm đến.'
        : route && noPath ? 'Không có tuyến để đóng thêm. Bấm Mở lại tất cả, đổi điều kiện giao thông, hoặc Xóa để chọn điểm mới.'
        : route ? 'Bấm vào một đoạn trên tuyến để đóng đoạn đó. Bấm Xóa để chọn điểm mới.'
          : 'Bấm Tìm đường. Bấm lên bản đồ lần nữa để chọn lại từ đầu.')
    : (!depot ? 'Bấm lên bản đồ để đặt kho.'
      : tour?.status === 'ok' ? 'Bấm vào một đoạn trên tour để đóng đoạn đó; tour được lập lại. Bấm Xóa để lập tour mới.'
        : tour ? 'Bấm Mở lại tất cả để bỏ các đoạn đang đóng, hoặc Xóa để lập tour mới.'
          : `Bấm để thêm điểm giao (tối đa ${MAX_TOUR_STOPS}), rồi bấm Lập tour.`
            + (tourBlocked.length ? ' Các đoạn đang đóng vẫn giữ khi lập tour mới; bấm Mở lại tất cả để bỏ.' : ''))

  // Đợt UI "Bàn điều phối" (họp thiết kế 9 vai, Tiến duyệt mockup 16/11): một bố cục cho mọi độ rộng từ 768 px.
  // Panel trái ba tầng: tóm tắt kết quả (luôn thấy) / phần giữa cuộn được / đáy dính có điều kiện giao thông và nút
  // chính. Bản đồ bên phải, khay phân tích dưới bản đồ thu gọn được; không lớp nào che tuyến.
  const summaryBlock = (
    <VStack gap={2} as="section" aria-label="Kết quả đo được">
      <Heading level={2}>Kết quả đo được</Heading>
      {summaryKpi ? (
        <VStack gap={1}>
          <Grid columns={2} gap={2}>
            <Kpi label="Thời gian di chuyển ước tính" value={minutes(summaryKpi.cost)}
              sub={`${summaryKpi.timeNote} · ${secondsRaw(summaryKpi.cost)}`} />
            <Kpi label="Quãng đường" value={km(summaryKpi.dist)} sub={metersRaw(summaryKpi.dist)} />
          </Grid>
          {/* Tour: so theo phương án được chọn như dòng ở khay kết quả, nên ghi rõ (góp ý #160). */}
          {summaryKpi.delta && (
            <Text type="body" weight="semibold">
              So với lần trước{mode === 'tour' ? ', phương án được chọn' : ''}: {summaryKpi.delta}
            </Text>
          )}
          {/* Bước 10 của DEMO: số "Giữ thứ tự cũ" thấy ngay ở máy chiếu, không phải cuộn tới danh sách phương án. */}
          {mode === 'tour' && tour?.candidates.kept_order && (
            <Text type="body" hasTabularNumbers>
              Giữ thứ tự cũ: {minutesText(tour.candidates.kept_order.cost_s)} · {secondsRaw(tour.candidates.kept_order.cost_s)}
            </Text>
          )}
        </VStack>
      ) : summary ? (
        <Text type="body" weight="semibold">{summary}</Text>
      ) : (
        <Text type="supporting">Chưa có kết quả.</Text>
      )}
    </VStack>
  )

  const status = (
    <>
      {checkingPoints > 0 && <Spinner label="Đang kiểm điểm vừa chọn…" />}
      {(mode === 'route' ? busyRoute : busyTour) && <Spinner label="Đang tính…" />}
      {notice && <Banner status="info" title={notice} />}
      {/* role="alert": lỗi được đọc ngay cho người dùng trình đọc màn hình (FE-3). */}
      {errorState && errorState.mode === mode && <Banner status="error" title={errorState.text} role="alert" />}
      {mode === 'route' && noPath && (
        <Banner status="info" title="Không có đường đi giữa hai điểm này với điều kiện giao thông hiện tại." />
      )}
    </>
  )

  const middle = (
    <VStack gap={4}>
      {status}
      <Selector
        label="Lộ trình mẫu"
        placeholder="Chọn lộ trình mẫu"
        options={DEMO_CASES.map((c) => ({ value: c.id, label: c.label }))}
        value={caseId}
        onChange={loadCase}
        isDisabled={caseDisabled}
        disabledMessage={`Lộ trình mẫu dùng đồ thị ${DEMO_DATASET_ID}, server đang nạp ${datasetId}.`}
      />
      <Divider />
      <VStack gap={3}>
        <Heading level={3}>{mode === 'route' ? 'Điểm đi và điểm đến' : 'Kho và điểm giao'}</Heading>
        <Text type="supporting">{hint}</Text>
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
          <VStack gap={1}>
            <HStack gap={2} vAlign="center">
              <StatusDot variant={source ? 'success' : 'neutral'} label={source ? 'Đã đặt điểm đi' : 'Chưa đặt điểm đi'} />
              <Text type="body">Điểm đi: {fmt(source)}</Text>
            </HStack>
            <HStack gap={2} vAlign="center">
              <StatusDot variant={target ? 'error' : 'neutral'} label={target ? 'Đã đặt điểm đến' : 'Chưa đặt điểm đến'} />
              <Text type="body">Điểm đến: {fmt(target)}</Text>
            </HStack>
          </VStack>
        ) : (
          <HStack gap={2} vAlign="center">
            <StatusDot variant={depot ? 'success' : 'neutral'} label={depot ? 'Đã đặt kho' : 'Chưa đặt kho'} />
            <Text type="body">
              {!depot ? 'Chưa đặt kho' : depot.label === 'Kho' ? 'Đã đặt kho' : `Kho: ${depot.label}`} · {stops.length} điểm giao
            </Text>
          </HStack>
        )}
        <HStack gap={2}>
          {mode === 'route'
            ? <Button label="Đảo chiều" size="sm" isDisabled={!(source && target) || checking} onClick={swap} />
            : <Button label="Bỏ điểm cuối" size="sm" isDisabled={!depot} onClick={removeLastPoint} />}
        </HStack>
      </VStack>
      {(keySegs.length > 0 || (mode === 'route' ? blocked : tourBlocked).length > 0) && (
        <>
          <Divider />
          <VStack gap={3}>
            {(mode === 'route' ? blocked : tourBlocked).length > 0 && (
              <HStack gap={2} vAlign="center" hAlign="between">
                <Text type="supporting">Đang đóng {(mode === 'route' ? blocked : tourBlocked).length} cạnh</Text>
                <Button label="Mở lại tất cả" size="sm" onClick={reopenAll} />
              </HStack>
            )}
            {keySegs.length > 0 && (
              <Selector
                label={mode === 'route' ? 'Đóng một đoạn trên tuyến' : 'Đóng một đoạn trên tour'}
                placeholder="Chọn đoạn (thay cho bấm trên bản đồ)"
                options={keyLabels.map((label, i) => ({ value: String(i), label }))}
                value=""
                onChange={closeByKey}
              />
            )}
          </VStack>
        </>
      )}
    </VStack>
  )

  // Đáy dính: điều kiện giao thông cạnh nút chính, vì đổi điều kiện rồi tính lại là thao tác hay làm nhất khi demo.
  const footer = (
    <VStack gap={3}>
      <Selector
        label="Điều kiện giao thông"
        options={scenarios.map((s) => ({ value: s.id, label: s.label }))}
        value={scenarioId}
        onChange={changeScenario}
      />
      {scenarioNote && <Text type="supporting">{scenarioNote}</Text>}
      {mode === 'route' ? (
        <HStack gap={2}>
          <StackItem size="fill">
            <Button label="Tìm đường" variant="primary" width="100%" isDisabled={!(source && target) || checking} onClick={findRoute} />
          </StackItem>
          <Button label="Xóa" variant="ghost" onClick={clearAll} />
        </HStack>
      ) : (
        <HStack gap={2}>
          <StackItem size="fill">
            <Button label="Lập tour" variant="primary" width="100%" isDisabled={!depot || stops.length === 0 || checking} onClick={buildTour} />
          </StackItem>
          <Button label="Xóa" variant="ghost" onClick={clearAll} />
        </HStack>
      )}
    </VStack>
  )

  // Trạng thái rỗng có bước tiếp theo (đợt UI 15/11) thay dòng "Chưa có kết quả.".
  const sampleId = mode === 'route' ? 'hai-diem-qua-trung-tam' : 'kho-5-diem'
  const empty = (
    <EmptyState isCompact headingLevel={3}
      title={mode === 'route' ? 'Chưa có tuyến' : 'Chưa có tour'}
      description={mode === 'route'
        ? 'Đặt điểm đi và điểm đến trên bản đồ hoặc từ danh sách địa danh, rồi bấm Tìm đường. Hoặc mở một lộ trình mẫu.'
        : 'Đặt kho rồi các điểm giao, sau đó bấm Lập tour. Hoặc mở một lộ trình mẫu.'}
      actions={DEMO_CASES.some((c) => c.id === sampleId) && !caseDisabled
        ? <Button label="Mở lộ trình mẫu" size="sm" onClick={() => loadCase(sampleId)} />
        : undefined}
    />
  )
  const results = mode === 'route'
    ? (route ? <RouteResults res={route.res} scenarioLabel={routeScenarioLabel} hasSummary
      previous={prevRoute ? { res: prevRoute.res, label: runLabel(prevRoute) } : null} /> : empty)
    : (tour ? <TourResults res={tour} labels={tourLabels} hasSummary selected={tourMethod} onSelect={setTourMethod} scenarioLabel={tourScenarioLabel}
      previous={prevTour ? { res: prevTour.res, label: runLabel(prevTour), closedMore: closedMore(prevTour, tourScenario) } : null} />
      : empty)

  // Khay phân tích dưới bản đồ: thu về một dòng tiêu đề để bản đồ cao hơn; đổi xong thì thu phóng lại cho vừa tuyến.
  const trayTitle = mode === 'route' ? 'Phân tích thuật toán' : 'So sánh phương án'
  const trayHeader = (
    <HStack gap={3} vAlign="center" hAlign="between" wrap="wrap">
      <Heading level={2}>{trayTitle}</Heading>
      <HStack gap={4} vAlign="center" wrap="wrap">
      {mode === 'route' && (
        <Switch label="Hiện node đã mở rộng" value={showTrace} onChange={setShowTrace}
          description={narrow ? 'Chấm xám: Dijkstra · chấm cam: A*. Lấy bằng một lần tìm riêng, không tính vào thời gian ở bảng.' : undefined} />
      )}
      <Switch label="Phần mở rộng" value={showExt} onChange={toggleExt}
        description={narrow ? (mode === 'route' ? 'Thêm ALT và Dijkstra hai chiều vào bảng (ngoài proposal).' : 'Thêm thẻ NN + 2-opt + Or-opt (ngoài proposal, chưa đo ở E5).') : undefined} />
      {!narrow && (
        <Button label={trayOpen ? 'Thu gọn' : 'Mở rộng'} variant="ghost" size="sm" aria-expanded={trayOpen}
          aria-controls="tray-body" onClick={toggleTray} />
      )}
      </HStack>
    </HStack>
  )
  const trayBody = (
    <VStack gap={3}>
      {mode === 'route' && showTrace && route && trace && <Text type="supporting">{traceLegend(trace)}</Text>}
      {results}
    </VStack>
  )

  const map = <MapView onReady={onMapReady} onClick={onMapClick} />
  const header = (
    // Header nền mực ở cả hai chế độ (đợt UI "Bàn điều phối"): bọc trong theme chế độ tối.
    <Theme theme={themes[defaultThemeSlug]} mode="dark">
    <LayoutHeader hasDivider>
      <HStack gap={4} vAlign="center" hAlign="between">
        <HStack gap={4} vAlign="center">
          <HStack gap={2} vAlign="center">
            <Logo />
            <Heading level={1}>SaiGo</Heading>
            {!medium && <Text type="supporting">Lập kế hoạch lộ trình giao hàng · Khu Bến Thành, TP.HCM</Text>}
          </HStack>
          <SegmentedControl label="Chế độ" value={mode} size="sm" onChange={(v) => changeMode(v as Mode)}>
            <SegmentedControlItem value="route" label="Tìm đường" />
            <SegmentedControlItem value="tour" label="Tour" />
          </SegmentedControl>
        </HStack>
        {/* Trạng thái gọn (đợt UI 15/11): chấm màu + chữ; mã dataset trong tooltip thay vì in ra như log. */}
        <Tooltip content={datasetId ? `Dữ liệu OSM: ${datasetId}` : server.text}>
          <HStack gap={2} vAlign="center">
            <StatusDot variant={server.ok === null ? 'neutral' : server.ok ? 'success' : 'error'} label={server.text} />
            {!narrow && <Text type="supporting">{server.ok === null ? 'Đang kết nối…' : server.ok ? 'Đã kết nối' : 'Mất kết nối'}</Text>}
          </HStack>
        </Tooltip>
      </HStack>
    </LayoutHeader>
    </Theme>
  )

  if (narrow) {
    // < 768 px: bản đồ ở trên (55% chiều cao), rồi kết quả, điều khiển và khay xếp dọc, cả trang cuộn.
    return (
      <AppShell height="fill">
        <Layout
          header={header}
          content={
            <LayoutContent padding={0} isScrollable label="Ứng dụng">
              <VStack gap={0}>
                <VStack height="55dvh">{map}</VStack>
                <VStack gap={6} padding={4}>
                  {summaryBlock}
                  {footer}
                  {middle}
                  <VStack gap={3} as="section" aria-label={trayTitle}>{trayHeader}{trayBody}</VStack>
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
          <LayoutPanel width={360} hasDivider padding={0} isScrollable={false} label="Bảng điều khiển">
            <VStack height="100%" gap={0}>
              <VStack padding={4} gap={0}>{summaryBlock}</VStack>
              <Divider />
              <StackItem size="fill" isScrollable>
                <VStack padding={4} gap={0}>{middle}</VStack>
              </StackItem>
              <Divider />
              <VStack padding={4} gap={0}>{footer}</VStack>
            </VStack>
          </LayoutPanel>
        }
        content={
          <LayoutContent padding={0} isScrollable={false} label="Bản đồ và phân tích">
            <VStack height="100%" gap={0}>
              <StackItem size="fill">{map}</StackItem>
              <Divider />
              <VStack as="section" aria-label={trayTitle} height={trayOpen ? TRAY_HEIGHT : undefined} gap={0}>
                <VStack paddingInline={4} paddingBlock={2} gap={0}>{trayHeader}</VStack>
                {/* Luôn render để aria-controls của nút Thu gọn / Mở rộng trỏ tới phần tử có thật; thu gọn thì hidden
                    (không nhận Tab, trình đọc màn hình bỏ qua). Góp ý review #165. */}
                <StackItem size="fill" isScrollable id="tray-body" hidden={!trayOpen}>
                  <VStack paddingInline={4} paddingBlockEnd={3} gap={0}>{trayBody}</VStack>
                </StackItem>
              </VStack>
            </VStack>
          </LayoutContent>
        }
      />
    </AppShell>
  )
}
