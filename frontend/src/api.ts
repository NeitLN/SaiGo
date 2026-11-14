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
  trace_limit?: number // > 0: trả thêm `trace` (toạ độ node đã mở rộng, theo thứ tự). Chỉ dùng cho lớp node đã mở rộng
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
  edge_ids?: number[] // thêm ngoài v1 (ARCHITECTURE mục 4)
  edge_twin_ids?: (number | null)[] // T51: cạnh đối của từng cạnh, cho "đóng đoạn" hai chiều (T54)
  edge_geometries?: [number, number][][] // T54 (#100): hình học [lon, lat] của từng cạnh, để biết người dùng bấm đoạn nào
  geometry: LineString
  expanded: number
  runtime_ms: number
  trace?: [number, number][] // [lon, lat] của node đã mở rộng theo thứ tự; rỗng nếu request không xin trace_limit
  trace_truncated?: boolean
}

// Thêm 14/11 (review UI, QA-3): cạnh đóng của request kèm hình học [lon, lat], để vẽ cả cạnh đóng sẵn của case.
export interface BlockedEdge {
  edge_id: number
  geometry: [number, number][]
}

export interface RouteResponse {
  dataset_id: string
  snapshot_id?: string | null
  snapped: { source: SnappedPoint; target: SnappedPoint }
  results: Partial<Record<Algorithm, AlgorithmResult>>
  costs_match?: boolean | null
  warnings?: string[]
  blocked_edges?: BlockedEdge[]
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
  node_count?: number
  edge_count?: number
  scenarios: Scenario[]
}

// Cùng nhãn với data/config/scenarios.json; chỉ dùng khi API chưa có /api/dataset.
export const BASELINE: Scenario = { id: 'baseline', label: 'Cơ sở — không ùn tắc, không đóng đường', rules: [] }

// POST /api/tour (T72; ARCHITECTURE mục 4).
export interface TourStop extends LatLon {
  id: string
}

export interface TourRequest {
  depot: LatLon
  stops: TourStop[]
  scenario_id?: string
  blocked_edge_ids?: number[]
  include_optimal?: boolean
  keep_order?: string[] // R1 C1: thứ tự id điểm giao trước khi đóng đường
}

// kept_order chỉ có khi request gửi keep_order (R1 C2); không bao giờ là `chosen`.
export type TourMethod = 'input' | 'nearest_neighbor' | 'nearest_neighbor_2opt' | 'kept_order'

export const TOUR_METHOD_LABEL: Record<TourMethod, string> = {
  input: 'Thứ tự nhập',
  nearest_neighbor: 'Nearest Neighbor',
  nearest_neighbor_2opt: 'NN + 2-opt',
  kept_order: 'Giữ thứ tự cũ',
}

export interface TourCandidate {
  stop_order: string[]
  cost_s: number
  distance_m: number
  improvement_pct: number
  edge_ids: number[]
  geometry: LineString
  edge_twin_ids?: (number | null)[]        // R1 C3, cùng định nghĩa với /api/route
  edge_geometries?: [number, number][][]
}

export interface TourResponse {
  dataset_id: string
  snapshot_id: string
  status: 'ok' | 'infeasible_under_model'
  snapped: Record<string, SnappedPoint & { id: string }>
  candidates: Partial<Record<TourMethod, TourCandidate>>
  chosen: TourMethod | null
  optimal?: { stop_order: string[]; cost_s: number; gap_pct: number } | null
  unreachable: { from_id: string; to_id: string }[]
  matrix_runtime_ms: number
  order_runtime_ms?: number | null
  warnings?: string[]
  blocked_edges?: BlockedEdge[]
}

export const MAX_TOUR_STOPS = 14 // khớp schemas.MAX_TOUR_STOPS của backend

// Mạng đường của vùng đang nạp, chỉ dùng làm nền khi không tải được tile OSM (T56 R8). Toạ độ [lon, lat].
export interface NetworkResponse {
  dataset_id: string
  lines: [number, number][][]
}

export async function getNetwork(): Promise<NetworkResponse> {
  const res = await fetch('/api/network')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
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

// Lỗi từ API: FastAPI trả `detail` là chuỗi tiếng Việt (dữ liệu sai với đồ thị, 503) hoặc danh sách
// lỗi kiểm tra kiểu của Pydantic (422, tiếng Anh) — ARCHITECTURE mục 4.
function errorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d) => {
      const e = d as { type?: string; msg?: string; ctx?: { max_length?: number } }
      // Lỗi giới hạn số phần tử là lỗi người dùng gặp được (UI chặn ở 14 nhưng API vẫn kiểm): ghi tiếng Việt.
      if (e.type === 'too_long' && e.ctx?.max_length !== undefined) return `Quá nhiều phần tử: tối đa ${e.ctx.max_length}.`
      return e.msg ?? JSON.stringify(d)
    }).join('; ')
  }
  return `HTTP ${status}`
}

const SERVER_DOWN = 'Không kết nối được server. Kiểm tra backend (uvicorn) đã chạy chưa.'

async function postJson<T>(path: string, req: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
      signal,
    })
  } catch (e) {
    if (signal?.aborted) throw e
    throw new Error(SERVER_DOWN)   // lỗi mạng: không tới được server
  }
  const body = await res.json().catch(() => null)
  // Backend tắt khi chạy qua proxy của Vite: proxy trả 502–504 không kèm JSON của FastAPI.
  if (body === null && res.status >= 502 && res.status <= 504) throw new Error(`${SERVER_DOWN} (HTTP ${res.status})`)
  if (!res.ok) throw new Error(errorMessage(res.status, body))
  return body as T
}

export const postRoute = (req: RouteRequest, signal?: AbortSignal) => postJson<RouteResponse>('/api/route', req, signal)

export const postTour = (req: TourRequest, signal?: AbortSignal) => postJson<TourResponse>('/api/tour', req, signal)
