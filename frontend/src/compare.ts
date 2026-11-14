// Chênh lệch trước/sau (review UI 14/11 đợt 2: PM-1, UX-5, AI-7). Khi đổi kịch bản hoặc đóng/mở đoạn mà vẫn
// cùng điểm, kết quả mới được so với kết quả ngay trước đó để người xem thấy hệ quả (RQ3), không phải tự nhớ
// số. Mọi số lấy từ hai response; module thuần để test bằng `node --test` (frontend/tests).

export type DeltaKind = 'changed' | 'same' | 'lost' | 'found' | 'both-none'

export interface Delta {
  kind: DeltaKind
  before: number | null      // giây; null = không có đường
  after: number | null
  diff: number | null        // after − before (giây), chỉ khi cả hai có đường
  pct: number | null         // 100 · diff / before
}

// Làm tròn về 0,1 s như số in ra trước khi trừ, để hiệu khớp phép trừ người xem tự làm trên hai số đang thấy
// (962,7 − 898,1 = 64,6, không phải 64,7 của số chưa làm tròn). Hai số bằng nhau sau làm tròn là "không đổi".
const r1 = (x: number) => Math.round(x * 10) / 10

export function costDelta(rawBefore: number | null, rawAfter: number | null): Delta {
  const before = rawBefore === null ? null : r1(rawBefore)
  const after = rawAfter === null ? null : r1(rawAfter)
  if (before === null && after === null) return { kind: 'both-none', before, after, diff: null, pct: null }
  if (before === null) return { kind: 'found', before, after, diff: null, pct: null }
  if (after === null) return { kind: 'lost', before, after, diff: null, pct: null }
  const diff = r1(after - before)
  if (diff === 0) return { kind: 'same', before, after, diff: 0, pct: 0 }
  return { kind: 'changed', before, after, diff, pct: before > 0 ? (100 * diff) / before : null }
}

const fmt = (x: number) => x.toLocaleString('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const signed = (x: number) => `${x > 0 ? '+' : '−'}${fmt(Math.abs(x))}`

/** Một dòng: "186,1 s → 300,0 s: +113,9 s (+61,2%)". */
export function deltaText(d: Delta): string {
  switch (d.kind) {
    case 'both-none': return 'trước và sau đều không có đường'
    case 'found': return `trước không có đường → ${fmt(d.after!)} s`
    case 'lost': return `${fmt(d.before!)} s → không còn đường`
    case 'same': return `không đổi (${fmt(d.after!)} s)`
    case 'changed': {
      const pct = d.pct === null ? '' : ` (${signed(d.pct)}%)`
      return `${fmt(d.before!)} s → ${fmt(d.after!)} s: ${signed(d.diff!)} s${pct}`
    }
  }
}

/** Hai response có cùng bộ điểm (so bằng node đã snap, theo khóa), để biết có so được không. */
export function samePoints(a: Record<string, number>, b: Record<string, number>): boolean {
  const ka = Object.keys(a)
  return ka.length === Object.keys(b).length && ka.every((k) => b[k] === a[k])
}

/** Hai danh sách cạnh đóng giống nhau như tập hợp. */
export function sameIds(a: number[], b: number[]): boolean {
  const sa = new Set(a)
  return sa.size === new Set(b).size && b.every((x) => sa.has(x))
}
