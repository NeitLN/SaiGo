// Giải thích tour không khả thi (R1 C4, review 14/11 UX-4 / QA-14, review #135): từ danh sách cặp không đi
// được, chọn ít điểm nhất mà mọi cặp đều dính tới một điểm đã chọn. Điểm được chọn là điểm tô đỏ trên bản đồ,
// mỗi điểm một dòng. Module thuần (không React) để test bằng `node --test` (frontend/tests).

export interface UnreachablePair { from_id: string; to_id: string }

/** Một điểm "hỏng": `noReachFrom` = các điểm không đi tới được nó; `noReachTo` = các điểm nó không đi tới được. */
export interface PointIssue { id: string; noReachFrom: string[]; noReachTo: string[] }

/**
 * Phủ tham lam: mỗi bước chọn điểm nằm trong nhiều cặp chưa được giải thích nhất (tính cả khi là điểm đi lẫn
 * điểm đến), hòa thì lấy điểm xuất hiện trước trong danh sách. Một điểm bị chặn hết đường vào, hết đường ra,
 * hay cả hai đều nằm trong mọi cặp hỏng nên chỉ ra một điểm. Trước đây gom riêng theo điểm đến hoặc điểm đi:
 * điểm bị chặn cả hai chiều làm cả hai cách đều ra n nhóm, tô đỏ mọi điểm (review #135).
 */
export function unreachableGroups(pairs: UnreachablePair[]): PointIssue[] {
  const order: string[] = []
  for (const p of pairs) {
    if (!order.includes(p.from_id)) order.push(p.from_id)
    if (!order.includes(p.to_id)) order.push(p.to_id)
  }
  let left = [...pairs]
  const issues: PointIssue[] = []
  while (left.length) {
    let best = order[0]
    let bestCount = -1
    for (const id of order) {
      const n = left.filter((p) => p.from_id === id || p.to_id === id).length
      if (n > bestCount) {
        best = id
        bestCount = n
      }
    }
    const mine = left.filter((p) => p.from_id === best || p.to_id === best)
    issues.push({
      id: best,
      noReachFrom: mine.filter((p) => p.to_id === best).map((p) => p.from_id),
      noReachTo: mine.filter((p) => p.from_id === best).map((p) => p.to_id),
    })
    left = left.filter((p) => p.from_id !== best && p.to_id !== best)
  }
  return issues
}

/**
 * Một câu cho một điểm hỏng. `others` = số điểm còn lại (kể cả kho) để biết "mọi điểm"; `name` đổi id ra tên.
 */
export function describeIssue(g: PointIssue, others: number, name: (id: string) => string): string {
  const n = name(g.id)
  const allIn = g.noReachFrom.length === others
  const allOut = g.noReachTo.length === others
  if (allIn && allOut) return `${cap(n)} bị cô lập: không đi tới được và cũng không đi ra được.`
  const parts: string[] = []
  if (allIn) parts.push(`không điểm nào đi tới được ${n}`)
  else if (g.noReachFrom.length) parts.push(`không đi tới được ${n} từ: ${g.noReachFrom.map(name).join(', ')}`)
  if (allOut) parts.push(`từ ${n} không đi được tới điểm nào`)
  else if (g.noReachTo.length) parts.push(`từ ${n} không đi tới được: ${g.noReachTo.map(name).join(', ')}`)
  return `${cap(parts.join('; '))}.`
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
