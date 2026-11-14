// Hình học phẳng gần đúng cho các lớp vẽ (vùng demo ~2 km nên coi mặt đất là phẳng quanh từng đoạn).
// Module thuần để test bằng `node --test` (frontend/tests).

const M_PER_DEG = 111_320   // mét trên 1 độ vĩ; 1 độ kinh = M_PER_DEG · cos(vĩ độ)

export interface Arrow { lat: number; lon: number; bearing: number }   // bearing: độ, 0 = bắc, theo chiều kim đồng hồ

/**
 * Điểm đặt mũi tên chỉ chiều dọc một tuyến `[lon, lat]` (review UI 14/11 đợt 3, UX-9): cách đều `spacingM`
 * mét tính từ đầu tuyến, bỏ hai đầu; hướng là hướng của đoạn chứa điểm đó.
 */
export function arrowPoints(coords: [number, number][], spacingM: number): Arrow[] {
  const out: Arrow[] = []
  let next = spacingM
  let walked = 0
  for (let i = 1; i < coords.length; i++) {
    const [lon1, lat1] = coords[i - 1]
    const [lon2, lat2] = coords[i]
    const kx = M_PER_DEG * Math.cos(((lat1 + lat2) / 2) * (Math.PI / 180))
    const dx = (lon2 - lon1) * kx
    const dy = (lat2 - lat1) * M_PER_DEG
    const len = Math.hypot(dx, dy)
    if (len === 0) continue
    const bearing = ((Math.atan2(dx, dy) * 180) / Math.PI + 360) % 360
    while (walked + len >= next) {
      const t = (next - walked) / len
      out.push({ lat: lat1 + t * (lat2 - lat1), lon: lon1 + t * (lon2 - lon1), bearing })
      next += spacingM
    }
    walked += len
  }
  // Mũi tên trùng điểm cuối (tuyến dài đúng bội số khoảng cách) thì bỏ, để không đè lên marker.
  if (out.length && walked - (next - spacingM) < 1e-6) out.pop()
  return out
}
