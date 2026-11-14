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
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'
import {
  BASELINE, MAX_TOUR_STOPS, getDataset, getHealth, postRoute, postTour,
  type BlockedEdge, type LatLon, type RouteResponse, type Scenario, type TourMethod, type TourResponse,
} from './api'
import { DEMO_CASES, DEMO_DATASET_ID } from './cases'
import { toLatLngs, type MapLayers, type RouteSegment, type TourPoint } from './layers'
import MapView from './MapView'
import RouteResults from './RouteResults'
import TourResults from './TourResults'
import { unreachableGroups } from './tourIssues'

type Mode = 'route' | 'tour'

// Mỗi lần gửi request là một query mới (n tăng); effect hủy request cũ nên chỉ kết quả mới nhất được hiện.
interface RouteQuery { source: LatLon; target: LatLon; scenarioId: string; blocked: number[]; n: number }
// keepOrder (R1): thứ tự điểm giao trước khi đóng đường, để API trả thêm phương án "Giữ thứ tự cũ".
interface TourQuery { depot: TourPoint; stops: TourPoint[]; scenarioId: string; blocked: number[]; keepOrder?: string[]; n: number }

const fmt = (p: LatLon | null) => (p ? `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}` : '—')
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
  const layersRef = useRef<MapLayers | null>(null)
  const [mapReady, setMapReady] = useState(0)
  const onMapReady = useCallback((l: MapLayers) => {
    layersRef.current = l
    setMapReady((n) => n + 1)
  }, [])

  const [server, setServer] = useState<{ text: string; ok: boolean | null }>({ text: 'Đang kiểm tra server…', ok: null })
  const [datasetId, setDatasetId] = useState<string | null>(null)
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
  const [source, setSource] = useState<LatLon | null>(null)
  const [target, setTarget] = useState<LatLon | null>(null)
  const [closed, setClosed] = useState<RouteSegment[]>([])          // đoạn người dùng bấm đóng (T54)
  const [caseBlocked, setCaseBlocked] = useState<number[]>([])      // cạnh đóng sẵn của case demo
  const [routeQuery, setRouteQuery] = useState<RouteQuery | null>(null)
  // Giữ id kịch bản và số cạnh đóng của chính request đã trả về; nhãn tính lúc render từ danh sách kịch bản
  // hiện có, nên nạp lại danh sách không làm gọi lại /api/route (review #103).
  const [route, setRoute] = useState<{ res: RouteResponse; scenarioId: string; blockedCount: number } | null>(null)

  // Tour (T73)
  const [depot, setDepot] = useState<TourPoint | null>(null)
  const [stops, setStops] = useState<TourPoint[]>([])
  const [tourQuery, setTourQuery] = useState<TourQuery | null>(null)
  const [tour, setTour] = useState<TourResponse | null>(null)
  // Kịch bản và số cạnh đóng của chính request tour đã trả về, để thẻ tour ghi đúng kịch bản (QA-5).
  const [tourScenario, setTourScenario] = useState<{ scenarioId: string; blockedCount: number } | null>(null)
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
      source: routeQuery.source, target: routeQuery.target, algorithms: ['dijkstra', 'astar'],
      scenario_id: routeQuery.scenarioId, blocked_edge_ids: routeQuery.blocked,
    }, ctl.signal)
      .then((res) => {
        setRoute({ res, scenarioId: routeQuery.scenarioId, blockedCount: routeQuery.blocked.length })
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
        setTour(res)
        setTourScenario({ scenarioId: tourQuery.scenarioId, blockedCount: tourQuery.blocked.length })
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
    if (mode === 'route') {
      layers.setClosed(closedToDraw(route?.res.blocked_edges, closed))
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
      layers.setClosed(closedToDraw(tour?.blocked_edges, tourClosed))
      const cand = tour && tourMethod ? tour.candidates[tourMethod] : undefined
      const broken = new Set(tour?.status === 'infeasible_under_model' ? unreachableGroups(tour.unreachable).map((g) => g.id) : [])
      layers.setTourPoints(depot, stops, cand?.stop_order, broken)
      if (cand) layers.drawTour(cand, closeTourSegment)
      else layers.clearRoutes()
      if (tour && pendingFit.current) {
        pendingFit.current = false
        const pts = Object.values(tour.snapped).map((p): [number, number] => [p.lon, p.lat])
        layers.fitTo(toLatLngs([...pts, ...(cand?.geometry.coordinates ?? [])]))
      }
    }
  }, [mapReady, mode, scenario, route, source, target, closed, closeSegment, tour, tourMethod, depot, stops,
    tourClosed, closeTourSegment])

  // --- Thao tác ---

  const resetRoute = () => {
    setRouteQuery(null)
    setRoute(null)
    setTarget(null)
    setClosed([])
    setCaseBlocked([])
    setError(null)
  }

  const resetTour = () => {
    setTourQuery(null)
    setTour(null)
    setTourScenario(null)
    setTourMethod(null)
    setError(null)
  }

  // Đang hiện kết quả thì cú bấm lên bản đồ không xoá gì (QA-1): một cú bấm trượt khỏi tuyến trong lúc demo
  // từng xoá cả tuyến lẫn các đoạn đã đóng. Muốn chọn lại thì bấm Xóa.
  const onMapClick = (p: LatLon) => {
    if (mode === 'route') {
      if (route) {
        setNotice('Đang hiện kết quả nên cú bấm lên bản đồ được bỏ qua. Bấm Xóa để chọn điểm mới.')
        return
      }
      setCaseId('')
      setNotice(null)
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
    if (!depot) setDepot({ ...p, id: 'depot', label: 'Kho' })
    else setStops([...stops, { ...p, id: `p${stops.length + 1}`, label: `Điểm ${stops.length + 1}` }])
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
    setMode(v)
    setError(null)
    setNotice(null)
    // Ô case demo không giữ tên case của chế độ kia (UX-11).
    if (DEMO_CASES.find((c) => c.id === caseId)?.mode !== v) setCaseId('')
  }

  const clearAll = () => {
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
      setRoute(null)
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
      setTour(null)
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
  const routeScenarioBase = route ? (scenarios.find((s) => s.id === route.scenarioId)?.label ?? route.scenarioId) : ''
  const routeScenarioLabel = route && route.blockedCount > 0
    ? `${routeScenarioBase}; đóng thêm ${route.blockedCount} cạnh` : routeScenarioBase
  const tourScenarioBase = tourScenario
    ? (scenarios.find((s) => s.id === tourScenario.scenarioId)?.label ?? tourScenario.scenarioId) : ''
  const tourScenarioLabel = tourScenario && tourScenario.blockedCount > 0
    ? `${tourScenarioBase}; đóng thêm ${tourScenario.blockedCount} cạnh` : tourScenarioBase

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
        </VStack>
      ) : (
        <VStack gap={2}>
          <Text type="supporting">
            {!depot ? 'Chưa đặt kho' : depot.label === 'Kho' ? 'Đã đặt kho' : `Kho: ${depot.label}`} · {stops.length} điểm giao
          </Text>
          <HStack gap={2}>
            <Button label="Lập tour" variant="primary" isDisabled={!depot || stops.length === 0} onClick={buildTour} />
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
    ? (route ? <RouteResults res={route.res} scenarioLabel={routeScenarioLabel} /> : <Text type="supporting">Chưa có kết quả.</Text>)
    : (tour ? <TourResults res={tour} labels={tourLabels} selected={tourMethod} onSelect={setTourMethod} scenarioLabel={tourScenarioLabel} />
      : <Text type="supporting">Chưa có kết quả.</Text>)

  return (
    <AppShell height="fill">
      <Layout
        header={
          <LayoutHeader hasDivider>
            <HStack gap={3} vAlign="center" hAlign="between">
              <HStack gap={2} vAlign="center">
                <Heading level={1}>SaiGo</Heading>
                <Text type="supporting">Lập kế hoạch lộ trình giao hàng</Text>
              </HStack>
              <Badge variant={server.ok === null ? 'neutral' : server.ok ? 'success' : 'error'} label={server.text} />
            </HStack>
          </LayoutHeader>
        }
        start={<LayoutPanel width={320} hasDivider padding={4} label="Bảng điều khiển">{controls}</LayoutPanel>}
        content={
          <LayoutContent padding={0} isScrollable={false} label="Bản đồ">
            <MapView onReady={onMapReady} onClick={onMapClick} />
          </LayoutContent>
        }
        end={
          <LayoutPanel width={380} hasDivider padding={4} label="Kết quả đo được">
            <VStack gap={3}>
              <Heading level={2}>Kết quả đo được</Heading>
              {results}
            </VStack>
          </LayoutPanel>
        }
      />
    </AppShell>
  )
}
