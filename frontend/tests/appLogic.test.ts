// Logic state của App (tách khỏi App.tsx sau review UI 14/11). Chạy: cd frontend; npm test.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  addTourPoint, blockedIds, distanceText, fmt, nextPrevious, nextRoutePoint, removeLastTourPoint, renameIds,
  routeAnnouncement, sameIdList, tourAnnouncement, traceLegend, type Run, type TourPt,
} from '../src/appLogic.ts'
import type { RouteResponse, TourResponse } from '../src/api.ts'

const A = { lat: 10.77, lon: 106.69 }
const B = { lat: 10.78, lon: 106.70, name: 'Bitexco' }

test('nextRoutePoint: điểm đi, điểm đến, đủ hai điểm thì bắt đầu lại', () => {
  assert.deepEqual(nextRoutePoint(null, null, A), { source: A, target: null, restart: true })
  assert.deepEqual(nextRoutePoint(A, null, B), { source: A, target: B, restart: false })
  assert.deepEqual(nextRoutePoint(A, B, B), { source: B, target: null, restart: true })
})

test('fmt: có tên thì hiện tên, không thì toạ độ 5 chữ số, rỗng là gạch', () => {
  assert.equal(fmt(B), 'Bitexco')
  assert.equal(fmt(A), '10.77000, 106.69000')
  assert.equal(fmt(null), '—')
})

test('addTourPoint: điểm đầu là kho, rồi p1, p2; giữ tên địa danh, tên mặc định "Điểm n"', () => {
  const r1 = addTourPoint(null, [], { ...A, name: 'Chợ Bến Thành' }, 14)
  assert.equal(r1.kind, 'depot')
  const depot = (r1 as { depot: TourPt }).depot
  assert.deepEqual(depot, { lat: A.lat, lon: A.lon, id: 'depot', label: 'Chợ Bến Thành' })
  const r2 = addTourPoint(depot, [], B, 14)
  assert.deepEqual(r2, { kind: 'stop', stops: [{ lat: B.lat, lon: B.lon, id: 'p1', label: 'Bitexco' }] })
  const r3 = addTourPoint(depot, (r2 as { stops: TourPt[] }).stops, { lat: 10.79, lon: 106.71 }, 14)
  assert.equal((r3 as { stops: TourPt[] }).stops[1].label, 'Điểm 2')
  assert.equal(addTourPoint(null, [], A, 14).kind === 'depot' && (addTourPoint(null, [], A, 14) as { depot: TourPt }).depot.label, 'Kho')
})

test('addTourPoint: chặn khi đủ số điểm giao và khi trùng toạ độ (không đổi gì)', () => {
  const depot: TourPt = { ...A, id: 'depot', label: 'Kho' }
  const full = Array.from({ length: 3 }, (_, i) => ({ lat: 10.8 + i, lon: 106.7, id: `p${i + 1}`, label: `Điểm ${i + 1}` }))
  assert.deepEqual(addTourPoint(depot, full, B, 3), { kind: 'error', text: 'Tối đa 3 điểm giao.' })
  assert.deepEqual(addTourPoint(depot, [], A, 14), { kind: 'error', text: '"Kho" đã có trong tour.' })
  assert.deepEqual(addTourPoint(depot, full, { lat: 10.8, lon: 106.7 }, 14), { kind: 'error', text: '"Điểm 1" đã có trong tour.' })
})

test('removeLastTourPoint: bỏ điểm giao cuối; hết điểm giao thì bỏ kho', () => {
  const depot: TourPt = { ...A, id: 'depot', label: 'Kho' }
  const s: TourPt[] = [{ ...B, id: 'p1', label: 'Bitexco' }]
  assert.deepEqual(removeLastTourPoint(depot, s), { depot, stops: [] })
  assert.deepEqual(removeLastTourPoint(depot, []), { depot: null, stops: [] })
})

test('blockedIds: cạnh đóng sẵn trước, mỗi đoạn bấm thêm cạnh và cạnh đối, bỏ trùng', () => {
  assert.deepEqual(blockedIds([1666], [{ edgeId: 5, twinId: 6 }, { edgeId: 7, twinId: null }, { edgeId: 6, twinId: 5 }]), [1666, 5, 6, 7])
  assert.deepEqual(blockedIds([], []), [])
})

test('sameIdList phân biệt thứ tự', () => {
  assert.ok(sameIdList([1, 2], [1, 2]))
  assert.ok(!sameIdList([1, 2], [2, 1]))
})

test('renameIds: id nội bộ thành tên trên marker, id lạ giữ nguyên', () => {
  const stops: TourPt[] = [{ ...A, id: 'p2', label: 'Điểm 2' }]
  assert.equal(renameIds("Điểm giao 'p2' trùng node 113 với 'depot'", stops), 'Điểm giao "Điểm 2" trùng node 113 với "kho"')
  assert.equal(renameIds("kịch bản 'xyz' không có", stops), "kịch bản 'xyz' không có")
})

test('distanceText: mét dưới 1 km, km một chữ số từ 1 km', () => {
  assert.equal(distanceText(162.4), '162 m')
  assert.equal(distanceText(33829), '33,8 km')
})

// --- mốc so trước/sau ---
const pts = (r: { p: number }) => ({ p: r.p })
const run = (p: number, scenarioId: string, blocked: number[]): Run<{ p: number }> => ({ res: { p }, scenarioId, blocked })

test('nextPrevious: cùng điểm khác kịch bản hoặc khác cạnh đóng thì lấy lần trước làm mốc', () => {
  const before = run(1, 'baseline', [])
  assert.equal(nextPrevious(before, run(1, 'peak', []), pts, null), before)
  assert.equal(nextPrevious(before, run(1, 'baseline', [5]), pts, null), before)
})

test('nextPrevious: cùng tham số thì giữ mốc đang có; khác điểm hoặc chưa có lần trước thì không có mốc', () => {
  const kept = run(1, 'baseline', [])
  assert.equal(nextPrevious(run(1, 'peak', [3, 4]), run(1, 'peak', [4, 3]), pts, kept), kept)
  assert.equal(nextPrevious(run(1, 'baseline', []), run(2, 'peak', []), pts, kept), null)
  assert.equal(nextPrevious(null, run(1, 'peak', []), pts, kept), null)
})

// --- câu đọc cho trình đọc màn hình ---
const route = (status: 'ok' | 'no_path') => ({
  results: {
    dijkstra: { status, cost_s: status === 'ok' ? 186.07 : null, distance_m: 1565, expanded: 404, trace_truncated: false },
    astar: { status, cost_s: status === 'ok' ? 186.07 : null, distance_m: 1565, expanded: 106, trace_truncated: true },
  },
}) as unknown as RouteResponse

test('routeAnnouncement và traceLegend lấy số từ response', () => {
  assert.equal(routeAnnouncement(route('ok')), 'Tìm xong: 186,1 giây, 1.565 mét. Dijkstra mở 404 node, A* mở 106 node.')
  assert.equal(routeAnnouncement(route('no_path')), 'Không có đường đi giữa hai điểm này trong kịch bản hiện tại.')
  assert.equal(traceLegend(route('ok')), 'Đang vẽ 404 node Dijkstra và 106 node A* đã mở rộng. Chỉ vẽ 5.000 node đầu.')
})

test('tourAnnouncement: phương án được chọn hoặc không khả thi', () => {
  const ok = { status: 'ok', chosen: 'nearest_neighbor_2opt', candidates: { nearest_neighbor_2opt: { cost_s: 898.07 } } }
  assert.equal(tourAnnouncement(ok as unknown as TourResponse), 'Lập tour xong: phương án được chọn 898,1 giây.')
  assert.equal(tourAnnouncement({ status: 'infeasible_under_model', chosen: null } as unknown as TourResponse),
    'Không lập được tour đầy đủ: có chặng không đi được.')
})
