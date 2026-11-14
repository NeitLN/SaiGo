// Review UI 14/11 đợt 2 (PM-1, UX-5, AI-7): chênh lệch trước/sau. Chạy: cd frontend; npm test.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { costDelta, deltaText, orderChanged, sameIds, samePoints } from '../src/compare.ts'

test('tăng chi phí: số giây và phần trăm, có dấu +', () => {
  const d = costDelta(186.1, 300.0)
  assert.equal(d.kind, 'changed')
  assert.ok(Math.abs(d.diff! - 113.9) < 1e-9)
  assert.equal(deltaText(d), '186,1 s → 300,0 s: +113,9 s (+61,2%)')
})

test('giảm chi phí: dấu trừ', () => {
  assert.equal(deltaText(costDelta(321.8, 300.0)), '321,8 s → 300,0 s: −21,8 s (−6,8%)')
})

test('hiệu tính trên số đã làm tròn như số in ra (962,7 − 898,1 = 64,6)', () => {
  assert.equal(deltaText(costDelta(898.07, 962.73)), '898,1 s → 962,7 s: +64,6 s (+7,2%)')
})

test('chênh dưới 0,05 s coi như không đổi', () => {
  const d = costDelta(186.1, 186.12)
  assert.equal(d.kind, 'same')
  assert.equal(deltaText(d), 'không đổi (186,1 s)')
})

test('mất đường và có lại đường', () => {
  assert.equal(costDelta(300, null).kind, 'lost')
  assert.equal(deltaText(costDelta(300, null)), '300,0 s → không còn đường')
  assert.equal(deltaText(costDelta(null, 204.7)), 'trước không có đường → 204,7 s')
  assert.equal(costDelta(null, null).kind, 'both-none')
})

test('cùng bộ điểm: so theo node đã snap, không theo thứ tự khóa', () => {
  assert.ok(samePoints({ depot: 5, p1: 7 }, { p1: 7, depot: 5 }))
  assert.ok(!samePoints({ depot: 5, p1: 7 }, { depot: 5, p1: 8 }))
  assert.ok(!samePoints({ depot: 5 }, { depot: 5, p1: 7 }))
  assert.ok(!samePoints({ source: 1, target: 2 }, { source: 2, target: 1 }))   // đảo chiều là cặp khác
})

test('so tập cạnh đóng không phụ thuộc thứ tự', () => {
  assert.ok(sameIds([3, 1], [1, 3]))
  assert.ok(!sameIds([1], [1, 3]))
})

test('bước 10 của DEMO: chênh lệch của phương án được chọn đi kèm việc đổi thứ tự (review #138)', () => {
  assert.equal(deltaText(costDelta(898.07, 692.5)), '898,1 s → 692,5 s: −205,6 s (−22,9%)')
  assert.ok(orderChanged(['p1', 'p2', 'p4', 'p3', 'p5'], ['p5', 'p1', 'p2', 'p4', 'p3']))
  assert.ok(!orderChanged(['p1', 'p2'], ['p1', 'p2']))
  assert.ok(!orderChanged(null, ['p1']))      // lần trước không khả thi: không có thứ tự để so
})
