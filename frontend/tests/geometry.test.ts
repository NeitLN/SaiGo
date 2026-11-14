// Mũi tên chỉ chiều trên tour (review UI 14/11 đợt 3, UX-9). Chạy: cd frontend; npm test.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { arrowPoints } from '../src/geometry.ts'

// 1 độ kinh tuyến ở vĩ độ 10,77 ≈ 109,35 km; 0,01° ≈ 1.093 m.
const EAST: [number, number][] = [[106.69, 10.77], [106.70, 10.77]]

test('đường thẳng hướng đông ~1,1 km, cách 200 m: 5 mũi tên, hướng 90°', () => {
  const a = arrowPoints(EAST, 200)
  assert.equal(a.length, 5)
  for (const p of a) {
    assert.ok(Math.abs(p.bearing - 90) < 0.5, `bearing ${p.bearing}`)
    assert.ok(Math.abs(p.lat - 10.77) < 1e-9)
  }
  assert.ok(a[0].lon > 106.69 && a[a.length - 1].lon < 106.70)   // nằm trong đoạn, không ở hai đầu
})

test('đi ngược chiều thì hướng 270°; hướng bắc 0°, hướng nam 180°', () => {
  assert.ok(Math.abs(arrowPoints([EAST[1], EAST[0]], 200)[0].bearing - 270) < 0.5)
  assert.ok(Math.abs(arrowPoints([[106.69, 10.77], [106.69, 10.78]], 200)[0].bearing - 0) < 0.5)
  assert.ok(Math.abs(arrowPoints([[106.69, 10.78], [106.69, 10.77]], 200)[0].bearing - 180) < 0.5)
})

test('đường gấp khúc: mũi tên theo hướng của đoạn chứa nó', () => {
  const L: [number, number][] = [[106.69, 10.77], [106.70, 10.77], [106.70, 10.78]]   // đông rồi bắc
  const a = arrowPoints(L, 200)
  assert.ok(a.some((p) => Math.abs(p.bearing - 90) < 0.5))
  assert.ok(a.some((p) => Math.abs(p.bearing) < 0.5))
})

test('tuyến ngắn hơn khoảng cách: không có mũi tên; rỗng hoặc một điểm: không có', () => {
  assert.deepEqual(arrowPoints([[106.69, 10.77], [106.6905, 10.77]], 200), [])
  assert.deepEqual(arrowPoints([], 200), [])
  assert.deepEqual(arrowPoints([[106.69, 10.77]], 200), [])
})
