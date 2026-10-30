// Kiểu dữ liệu theo contract v1 (docs/ARCHITECTURE.md mục 4.1). Bản sau chỉ được thêm trường.

export interface HealthResponse {
  status: string
  dataset_loaded: boolean
  dataset_id?: string | null
}

export interface LatLon {
  lat: number
  lon: number
}

export type Algorithm = 'dijkstra' | 'astar'

export interface RouteRequest {
  source: LatLon
  target: LatLon
  algorithms?: Algorithm[]
  scenario_id?: string
  blocked_edge_ids?: number[]
}

export interface SnappedPoint {
  node_id: number
  lat: number
  lon: number
  snap_distance_m: number
}

export interface LineString {
  type: 'LineString'
  coordinates: [number, number][] // [lon, lat] theo GeoJSON
}

export interface AlgorithmResult {
  status: 'ok' | 'no_path'
  cost_s: number | null
  distance_m: number | null
  edge_ids?: number[] // thêm ngoài v1 (ARCHITECTURE mục 4); T54 dùng để đóng đoạn trên tuyến
  edge_twin_ids?: (number | null)[] // cạnh đối (v → u) của từng cạnh, null nếu một chiều (T51)
  edge_geometries?: [number, number][][] // hình học [lon, lat] của từng cạnh (T54)
  geometry: LineString
  expanded: number
  runtime_ms: number
}

export interface RouteResponse {
  dataset_id: string
  snapshot_id?: string | null
  snapped: { source: SnappedPoint; target: SnappedPoint }
  results: Partial<Record<Algorithm, AlgorithmResult>>
  costs_match?: boolean | null
  warnings?: string[]
}

export const ALGORITHM_LABEL: Record<Algorithm, string> = { dijkstra: 'Dijkstra', astar: 'A*' }

// GET /api/dataset (T51). Kịch bản giữ đúng cấu trúc `saigo-scenarios/1` của data/config/scenarios.json
// và `CongestionZone` của backend/app/graph/scenario.py (DATA_MODEL mục 4.1).
export interface CongestionZone {
  type: string // hiện backend chỉ có 'circle'
  lat: number
  lon: number
  radius_m: number
}

export interface CongestionRule {
  zone: CongestionZone
  alpha: number
  highway?: string[] | null
}

export interface Scenario {
  id: string
  label: string
  rules: CongestionRule[]
}

export interface DatasetResponse {
  dataset_id: string
  scenarios: Scenario[]
}

// Cùng nhãn với data/config/scenarios.json; chỉ dùng khi API chưa có /api/dataset.
export const BASELINE: Scenario = { id: 'baseline', label: 'Cơ sở — không ùn tắc, không đóng đường', rules: [] }

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// null khi API chưa có /api/dataset (404): UI chỉ dùng kịch bản cơ sở.
export async function getDataset(): Promise<DatasetResponse | null> {
  const res = await fetch('/api/dataset')
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// Lỗi từ API: FastAPI trả `detail` là chuỗi (503) hoặc danh sách lỗi kiểm tra dữ liệu (422).
function errorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d) => (d as { msg?: string }).msg ?? JSON.stringify(d)).join('; ')
  }
  return `HTTP ${status}`
}

export async function postRoute(req: RouteRequest, signal?: AbortSignal): Promise<RouteResponse> {
  const res = await fetch('/api/route', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new Error(errorMessage(res.status, body))
  return body as RouteResponse
}

// POST /api/tour (T72). Chỉ số theo quy ước của backend/app/algorithms/tour.py: điểm 0 là kho,
// `order` khép kín bắt đầu bằng 0, tên phương án giống `TourPlan.method`.
export type TourMethod = 'input' | 'nearest_neighbor' | 'nearest_neighbor_2opt'

export const TOUR_LABEL: Record<TourMethod, string> = {
  input: 'Thứ tự nhập',
  nearest_neighbor: 'Nearest Neighbor',
  nearest_neighbor_2opt: 'NN + 2-opt',
}

export interface TourRequest {
  depot: LatLon
  stops: LatLon[]
  scenario_id?: string
}

export interface TourPlanOut {
  order: number[]
  cost_s: number
  distance_m: number
  geometry: LineString
}

export interface TourResponse {
  status: 'ok' | 'infeasible_under_model'
  snapped: SnappedPoint[] // snapped[i] ứng với điểm i (0 = kho)
  plans: Partial<Record<TourMethod, TourPlanOut>>
  chosen: TourMethod | null
  unreachable: [number, number][]
}

export async function postTour(req: TourRequest, signal?: AbortSignal): Promise<TourResponse> {
  const res = await fetch('/api/tour', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })
  if (res.status === 404) throw new Error('API chưa có /api/tour (T72).')
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new Error(errorMessage(res.status, body))
  return body as TourResponse
}
