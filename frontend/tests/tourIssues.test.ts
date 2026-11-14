// Chạy: cd frontend; npm test  (node --test, Node 24 tự bỏ kiểu TypeScript). Review #135.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { describeIssue, unreachableGroups, type UnreachablePair } from '../src/tourIssues.ts'

const IDS = ['depot', 'p1', 'p2', 'p3']
const others = IDS.length - 1
const name = (id: string) => (id === 'depot' ? 'kho' : id.toUpperCase())

const into = (x: string): UnreachablePair[] => IDS.filter((i) => i !== x).map((i) => ({ from_id: i, to_id: x }))
const outOf = (x: string): UnreachablePair[] => IDS.filter((i) => i !== x).map((i) => ({ from_id: x, to_id: i }))

test('chỉ chặn đường vào một điểm: một nhóm, đúng điểm đó', () => {
  const g = unreachableGroups(into('p2'))
  assert.deepEqual(g.map((x) => x.id), ['p2'])
  assert.deepEqual(g[0].noReachFrom, ['depot', 'p1', 'p3'])
  assert.deepEqual(g[0].noReachTo, [])
  assert.equal(describeIssue(g[0], others, name), 'Không điểm nào đi tới được P2.')
})

test('chỉ chặn đường ra một điểm: một nhóm, đúng điểm đó', () => {
  const g = unreachableGroups(outOf('p3'))
  assert.deepEqual(g.map((x) => x.id), ['p3'])
  assert.equal(describeIssue(g[0], others, name), 'Từ P3 không đi được tới điểm nào.')
})

test('chặn cả hai chiều một điểm: một nhóm "bị cô lập", không tô đỏ điểm khác', () => {
  const pairs = [...outOf('p2'), ...into('p2')]
  const g = unreachableGroups(pairs)
  assert.deepEqual(g.map((x) => x.id), ['p2'])
  assert.equal(describeIssue(g[0], others, name), 'P2 bị cô lập: không đi tới được và cũng không đi ra được.')
})

test('hai điểm hỏng độc lập: hai nhóm, mỗi cặp thuộc đúng một nhóm', () => {
  const pairs = [...into('p1'), ...outOf('p3').filter((p) => p.to_id !== 'p1')]
  const g = unreachableGroups(pairs)
  assert.deepEqual(new Set(g.map((x) => x.id)), new Set(['p1', 'p3']))
  const covered = g.reduce((n, x) => n + x.noReachFrom.length + x.noReachTo.length, 0)
  assert.equal(covered, pairs.length)
})

test('chặn một phần: nêu đúng các điểm', () => {
  const g = unreachableGroups([{ from_id: 'depot', to_id: 'p1' }, { from_id: 'p3', to_id: 'p1' }])
  assert.deepEqual(g.map((x) => x.id), ['p1'])
  assert.equal(describeIssue(g[0], others, name), 'Không đi tới được P1 từ: kho, P3.')
})

test('không có cặp nào: không có nhóm', () => {
  assert.deepEqual(unreachableGroups([]), [])
})
