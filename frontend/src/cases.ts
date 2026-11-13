// Case minh họa cho kịch bản demo (data/demo/cases.json, T55; DEMO mục 1.1). Tọa độ là tọa độ node đã
// snap trên dataset của file; UI chỉ dùng điểm và tham số, mọi số hiển thị vẫn lấy từ API.
import data from '../../data/demo/cases.json'

interface NamedPoint {
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
}

export const DEMO_DATASET_ID: string = data.dataset_id
export const DEMO_CASES: DemoCase[] = data.cases as DemoCase[]
