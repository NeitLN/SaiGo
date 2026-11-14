// Logic state của App tách thành hàm thuần (việc sau demo của review UI 14/11: tách state App.tsx kèm test).
// Không React, không Leaflet, để test bằng `node --test` (frontend/tests/appLogic.test.ts). Import có đuôi .ts
// để Node chạy được trực tiếp; Vite và tsc (allowImportingTsExtensions) cũng nhận.
import type { LatLon, RouteResponse, TourResponse } from './api.ts'
import { sameIds as sameIdSet, samePoints } from './compare.ts'

export type Mode = 'route' | 'tour'

/** Điểm có thể mang tên (chọn từ danh sách địa danh hoặc từ case): ô điểm đi/đến hiện tên thay cho toạ độ. */
export type Pt = LatLon & { name?: string }

/** Điểm của tour: kho có id 'depot', điểm giao p1, p2, … (cùng hình với TourPoint của layers.ts). */
export interface TourPt extends LatLon { id: string; label: string }

/** Một đoạn bấm đóng: cạnh và cạnh đối (cùng hình với phần dùng ở đây của RouteSegment trong layers.ts). */
export interface ClosedSeg { edgeId: number; twinId: number | null }

/** Lần chạy đã trả về: response kèm kịch bản và cạnh đóng của chính request đó (nhãn, so sánh trước/sau). */
export type Run<T> = { res: T; scenarioId: string; blocked: number[] }

export const fmt = (p: Pt | null) => (p ? (p.name ?? `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`) : '—')
export const latLon = (p: LatLon): LatLon => ({ lat: p.lat, lon: p.lon })   // không gửi tên lên API

/** Hai danh sách id giống hệt, kể cả thứ tự (query đã gửi so với danh sách cạnh đóng hiện tại). */
export const sameIdList = (a: number[], b: number[]) => a.length === b.length && a.every((x, i) => x === b[i])

/** Đóng đoạn = cạnh được bấm và cạnh đối của nó (DATA_MODEL 4.2); cạnh đóng sẵn của case đứng trước; bỏ trùng. */
export const blockedIds = (preset: number[], segs: ClosedSeg[]) =>
  [...new Set([...preset, ...segs.flatMap((s) => (s.twinId === null ? [s.edgeId] : [s.edgeId, s.twinId]))])]

export const routePoints = (r: RouteResponse) => ({ source: r.snapped.source.node_id, target: r.snapped.target.node_id })
export const tourPoints = (r: TourResponse) => Object.fromEntries(Object.entries(r.snapped).map(([k, v]) => [k, v.node_id]))

/**
 * Mốc so trước/sau cho kết quả mới (review 14/11 đợt 2, PM-1/UX-5/AI-7): chỉ khi cùng điểm mà khác kịch bản hoặc
 * khác cạnh đóng. Cùng điểm, cùng tham số (bấm lại Tìm đường, bật Phần mở rộng) thì giữ mốc đang có (`kept`);
 * khác điểm thì không có mốc.
 */
export function nextPrevious<T>(prev: Run<T> | null, next: Run<T>, pts: (r: T) => Record<string, number>,
  kept: Run<T> | null): Run<T> | null {
  if (!prev || !samePoints(pts(prev.res), pts(next.res))) return null
  if (prev.scenarioId === next.scenarioId && sameIdSet(prev.blocked, next.blocked)) return kept
  return prev
}

/**
 * Điểm vừa đặt ở chế độ tìm đường: lần 1 là điểm đi, lần 2 là điểm đến; đã đủ hai điểm (chưa tìm) thì bắt đầu lại
 * từ điểm đi (`restart`: App xoá tuyến, đoạn đóng, lỗi như resetRoute).
 */
export function nextRoutePoint(source: Pt | null, target: Pt | null, p: Pt):
  { source: Pt; target: Pt | null; restart: boolean } {
  if (!source || target) return { source: p, target: null, restart: true }
  return { source, target: p, restart: false }
}

export type AddTourPoint =
  | { kind: 'error'; text: string }
  | { kind: 'depot'; depot: TourPt }
  | { kind: 'stop'; stops: TourPt[] }

/**
 * Thêm một điểm vào tour đang dựng: điểm đầu là kho, sau đó là điểm giao p1, p2, …; giữ tên địa danh nếu có.
 * Từ chối khi đã đủ `max` điểm giao (QA-12) hoặc trùng toạ độ một điểm đã có (góp ý #145: chặn lúc chọn thay vì
 * để tới Lập tour mới báo "trùng node"); điểm chọn từ danh sách có toạ độ node chính xác nên so bằng toạ độ.
 */
export function addTourPoint(depot: TourPt | null, stops: TourPt[], p: Pt, max: number): AddTourPoint {
  if (depot && stops.length >= max) return { kind: 'error', text: `Tối đa ${max} điểm giao.` }
  const same = [...(depot ? [depot] : []), ...stops]
    .find((q) => Math.abs(q.lat - p.lat) < 1e-7 && Math.abs(q.lon - p.lon) < 1e-7)
  if (same) return { kind: 'error', text: `"${same.label}" đã có trong tour.` }
  if (!depot) return { kind: 'depot', depot: { ...latLon(p), id: 'depot', label: p.name ?? 'Kho' } }
  const n = stops.length + 1
  return { kind: 'stop', stops: [...stops, { ...latLon(p), id: `p${n}`, label: p.name ?? `Điểm ${n}` }] }
}

/** Bỏ điểm cuối (PM-7, U-2): bỏ điểm giao vừa thêm; hết điểm giao thì bỏ kho. */
export function removeLastTourPoint(depot: TourPt | null, stops: TourPt[]): { depot: TourPt | null; stops: TourPt[] } {
  return stops.length ? { depot, stops: stops.slice(0, -1) } : { depot: null, stops }
}

/** API gọi điểm bằng id nội bộ ('p2', 'depot'); đổi sang tên người dùng thấy trên marker (QA-13). */
export function renameIds(message: string, stops: TourPt[]): string {
  const names: Record<string, string> = Object.fromEntries(stops.map((s) => [s.id, s.label]))
  names.depot = 'kho'
  return message.replace(/'([\w-]+)'/g, (m, id: string) => (id in names ? `"${names[id]}"` : m))
}

/** Khoảng cách trong thông báo: dưới 1 km ghi mét, từ 1 km ghi km một chữ số (góp ý #142). */
export const distanceText = (m: number) =>
  m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} km`

const vn = (x: number, d = 1) => x.toLocaleString('vi-VN', { maximumFractionDigits: d })

/** Câu đọc cho trình đọc màn hình khi có kết quả tìm đường (FE-3); số lấy từ response. */
export function routeAnnouncement(r: RouteResponse): string {
  const d = r.results.dijkstra
  const a = r.results.astar
  if (!d || d.status !== 'ok' || d.cost_s === null) return 'Không có đường đi giữa hai điểm này trong kịch bản hiện tại.'
  const nodes = a ? ` Dijkstra mở ${vn(d.expanded, 0)} node, A* mở ${vn(a.expanded, 0)} node.` : ''
  return `Tìm xong: ${vn(d.cost_s)} giây, ${vn(d.distance_m ?? 0, 0)} mét.${nodes}`
}

/** Câu đọc khi có kết quả tour (FE-3). */
export function tourAnnouncement(r: TourResponse): string {
  if (r.status !== 'ok' || !r.chosen) return 'Không lập được tour đầy đủ: có chặng không đi được.'
  const c = r.candidates[r.chosen]
  return c ? `Lập tour xong: phương án được chọn ${vn(c.cost_s)} giây.` : 'Lập tour xong.'
}

/** Đủ cho mọi truy vấn trên vùng demo (lớn nhất 1.762 node khi không còn đường); backend giới hạn 5.000. */
export const TRACE_LIMIT = 5000

/** Chú thích lớp node đã mở rộng: số node của chính lần tìm có trace (bằng số ở bảng vì cùng tham số). */
export function traceLegend(r: RouteResponse): string {
  const d = r.results.dijkstra
  const a = r.results.astar
  if (!d || !a) return ''
  const cut = d.trace_truncated || a.trace_truncated ? ` Chỉ vẽ ${TRACE_LIMIT.toLocaleString('vi-VN')} node đầu.` : ''
  return `Đang vẽ ${d.expanded.toLocaleString('vi-VN')} node Dijkstra và ${a.expanded.toLocaleString('vi-VN')} node A* đã mở rộng.${cut}`
}
