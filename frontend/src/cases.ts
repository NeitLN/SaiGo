// Case minh họa cho kịch bản demo (data/demo/cases.json, T55; DEMO mục 1.1). Tọa độ là tọa độ node đã
// snap trên dataset của file; UI chỉ dùng điểm và tham số, mọi số hiển thị vẫn lấy từ API.
import data from '../../data/demo/cases.json'

export interface NamedPoint {
  name: string
  lat: number
  lon: number
}

export interface DemoCase {
  id: string
  label: string
  mode: 'route' | 'tour'
  source?: NamedPoint
  target?: NamedPoint
  depot?: NamedPoint
  stops?: NamedPoint[]
  scenario_id?: string
  blocked_edge_ids?: number[]
  // Thứ tự id điểm giao trước khi đóng đường (case dựng sẵn bước 10): gửi kèm để API trả "Giữ thứ tự cũ".
  keep_order?: string[]
}

export const DEMO_DATASET_ID: string = data.dataset_id
export const DEMO_CASES: DemoCase[] = data.cases as DemoCase[]

/**
 * Địa danh có tên lấy từ các case (review UI 14/11 đợt 3, phương án C-b): chọn từ danh sách thay vì bấm bản đồ,
 * dùng được bằng bàn phím và không cần dịch vụ tìm địa chỉ bên ngoài. Bỏ trùng theo tên; bỏ điểm đặt theo node
 * kỹ thuật (tên có "node"). Toạ độ là node đã snap trên dataset của file, nên luôn đạt ngưỡng snap.
 */
export const NAMED_PLACES: NamedPoint[] = (() => {
  const seen = new Map<string, NamedPoint>()
  for (const c of DEMO_CASES) {
    for (const p of [c.source, c.target, c.depot, ...(c.stops ?? [])]) {
      if (p && !/node/i.test(p.name) && !seen.has(p.name)) seen.set(p.name, p)
    }
  }
  return [...seen.values()].sort((a, b) => a.name.localeCompare(b.name, 'vi'))
})()
