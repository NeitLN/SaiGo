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

/** Cùng toạ độ (điểm đã kiểm được đặt đúng toạ độ node nên hai cú bấm vào cùng node trùng toạ độ). */
export const samePlace = (a: LatLon, b: LatLon) => Math.abs(a.lat - b.lat) < 1e-7 && Math.abs(a.lon - b.lon) < 1e-7

export type NextRoutePoint =
  | { kind: 'error'; text: string }
  | { kind: 'ok'; source: Pt; target: Pt | null; restart: boolean }

/**
 * Lần này chỉ đóng thêm đoạn so với lần trước: cùng kịch bản, tập cạnh đóng chứa hẳn tập lần trước. Chỉ khi đó phép
 * so "cùng thứ tự, trước khi đóng" mới nói đúng ảnh hưởng của việc đóng (test lại 15/11, T-1).
 */
export function closedMore(prev: { scenarioId: string; blocked: number[] } | null,
  now: { scenarioId: string; blocked: number[] } | null): boolean {
  if (!prev || !now || prev.scenarioId !== now.scenarioId) return false
  const cur = new Set(now.blocked)
  return cur.size > new Set(prev.blocked).size && prev.blocked.every((id) => cur.has(id))
}

/** Nhãn kịch bản kèm số cạnh đóng; nhãn cơ sở ghi "không đóng đường" nên bỏ vế đó khi có cạnh đóng (T-7). */
export function runLabel(scenarioLabel: string, blockedCount: number): string {
  if (blockedCount === 0) return scenarioLabel
  return `${scenarioLabel.replace(/, không đóng đường$/, '')}; đóng ${blockedCount} cạnh`
}

/**
 * Điểm vừa đặt ở chế độ tìm đường: lần 1 là điểm đi, lần 2 là điểm đến; đã đủ hai điểm (chưa tìm) thì bắt đầu lại
 * từ điểm đi (`restart`: App xoá tuyến, đoạn đóng, lỗi như resetRoute). Điểm đến trùng điểm đi thì từ chối (test
 * lại 15/11, R-9: trước đây ra tuyến 0 s, 0 m mà không báo gì; tour đã chặn trùng từ #145).
 */
export function nextRoutePoint(source: Pt | null, target: Pt | null, p: Pt): NextRoutePoint {
  if (!source || target) return { kind: 'ok', source: p, target: null, restart: true }
  if (samePlace(source, p)) return { kind: 'error', text: `Điểm đến trùng điểm đi (${fmt(source)}). Hãy chọn một điểm khác.` }
  return { kind: 'ok', source, target: p, restart: false }
}

export type AddTourPoint =
  | { kind: 'error'; text: string }
  | { kind: 'depot'; depot: TourPt }
  | { kind: 'stop'; stops: TourPt[] }

/**
 * Thêm một điểm vào tour đang dựng: điểm đầu là kho, sau đó là điểm giao p1, p2, …; giữ tên địa danh nếu có.
 * Từ chối khi đã đủ `max` điểm giao (QA-12) hoặc trùng toạ độ một điểm đã có (góp ý #145: chặn lúc chọn thay vì
 * để tới Lập tour mới báo "trùng node"); điểm chọn từ danh sách và điểm bấm đã kiểm (App đặt đúng toạ độ node
 * vừa snap, test lại 15/11 T-5) đều có toạ độ node, nên so bằng toạ độ là so node.
 */
export function addTourPoint(depot: TourPt | null, stops: TourPt[], p: Pt, max: number): AddTourPoint {
  if (depot && stops.length >= max) return { kind: 'error', text: `Tối đa ${max} điểm giao.` }
  const same = [...(depot ? [depot] : []), ...stops].find((q) => samePlace(q, p))
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

/**
 * Nhãn cho danh sách đóng đoạn bằng bàn phím (test lại 15/11, A-1): mỗi đoạn ghi thứ tự, độ dài và khoảng cách từ
 * điểm đầu tuyến/tour, để người không dùng chuột vẫn chọn được đoạn cần đóng.
 */
export function segmentLabels(lengths: number[], from: string): string[] {
  let before = 0
  return lengths.map((len, i) => {
    const label = `Đoạn ${i + 1}/${lengths.length}: ${Math.round(len)} m, bắt đầu cách ${from} ${distanceText(before)}`
    before += len
    return label
  })
}

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
