// Cột kết quả của chế độ tìm đường: bảng so sánh Dijkstra / A* (DEMO mục 1.3, nhãn bắt buộc ở mục 1.4).
import { Badge } from '@astryxdesign/core/Badge'
import { Banner } from '@astryxdesign/core/Banner'
import { HStack } from '@astryxdesign/core/HStack'
import { Table } from '@astryxdesign/core/Table'
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'
import { ALGORITHM_LABEL, type Algorithm, type AlgorithmResult, type RouteResponse } from './api'
import { costDelta, deltaText } from './compare'

const ALGOS: Algorithm[] = ['dijkstra', 'astar']
// Cùng màu với tuyến trên bản đồ (layers.ts: categorical blue / orange).
const LEGEND: Record<Algorithm, 'blue' | 'orange' | 'teal' | 'purple'> = {
  dijkstra: 'blue', astar: 'orange', alt: 'teal', bidijkstra: 'purple',
}
// Phần mở rộng (D17, đợt 3): bảng phụ riêng để bảng chính không chật; không vẽ tuyến riêng vì cùng chi phí.
const EXT: Algorithm[] = ['alt', 'bidijkstra']

export function num(x: number, digits = 1): string {
  return x.toLocaleString('vi-VN', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

export function seconds(s: number): string {
  return `${num(s)} s (${num(s / 60)} phút)`
}

const ROWS: [string, (r: AlgorithmResult) => string][] = [
  ['Thời gian di chuyển ước tính (theo kịch bản)', (r) => (r.status !== 'ok' || r.cost_s === null ? 'Không có đường' : seconds(r.cost_s))],
  ['Quãng đường', (r) => (r.status !== 'ok' || r.distance_m === null ? '—' : `${num(r.distance_m, 0)} m`)],
  ['Số node mở rộng', (r) => num(r.expanded, 0)],
  // Một lần chạy của truy vấn này (review 14/11, AI-1): nhãn nói rõ để không bị đọc thành kết luận tốc độ.
  ['Thời gian tính toán (1 lần chạy)', (r) => `${num(r.runtime_ms, 2)} ms`],
]
const EXT_ROWS: [string, (r: AlgorithmResult) => string][] = [ROWS[0], ROWS[2], ROWS[3]]

interface Row extends Record<string, unknown> {
  metric: string
  dijkstra?: string
  astar?: string
}

/** Dòng kết luận về chi phí (AI-2, QA-6): hai bên cùng không có đường thì không gọi là "chi phí trùng khớp". */
function costLine(res: RouteResponse): string {
  const d = res.results.dijkstra
  const a = res.results.astar
  if (d?.status === 'no_path' && a?.status === 'no_path') return 'Cả hai thuật toán cùng báo không có đường.'
  if (res.costs_match === true) return 'Chi phí trùng khớp: có'
  if (res.costs_match === false) return 'Chi phí trùng khớp: không'
  return 'Chi phí trùng khớp: —'
}

/** Tỉ lệ node A* so với Dijkstra trên chính truy vấn này (AI-3); chỉ khi cả hai tìm được đường. */
function nodeLine(res: RouteResponse): string | null {
  const d = res.results.dijkstra
  const a = res.results.astar
  if (!d || !a || d.status !== 'ok' || a.status !== 'ok' || d.expanded === 0) return null
  return `Ở truy vấn này, A* mở ${num((100 * a.expanded) / d.expanded, 0)}% số node của Dijkstra.`
}

/** Hai kết quả cùng chi phí (cùng không có đường cũng tính là cùng), sai số 1e-6 như costs_match của backend. */
function sameCost(a?: AlgorithmResult, b?: AlgorithmResult): boolean {
  if (!a || !b) return false
  if (a.status !== 'ok' || b.status !== 'ok') return a.status === b.status
  return Math.abs((a.cost_s ?? 0) - (b.cost_s ?? 0)) <= 1e-6 * Math.max(1, b.cost_s ?? 0)
}

/** Chi phí của tuyến (Dijkstra; A* luôn bằng khi cùng có đường) hoặc null nếu không có đường. */
const routeCost = (r: RouteResponse): number | null => {
  const d = r.results.dijkstra
  return d && d.status === 'ok' && d.cost_s !== null ? d.cost_s : null
}

export default function RouteResults({ res, scenarioLabel, previous }: {
  res: RouteResponse
  scenarioLabel: string
  // Lần trước cùng hai điểm, khác kịch bản hoặc cạnh đóng (review 14/11 đợt 2: PM-1, UX-5, AI-7).
  previous?: { res: RouteResponse; label: string } | null
}) {
  const algos = ALGOS.filter((a) => res.results[a])
  const data: Row[] = ROWS.map(([metric, f]) => {
    const row: Row = { metric }
    for (const a of algos) row[a] = f(res.results[a]!)
    return row
  })
  const nodes = nodeLine(res)
  const extAlgos = EXT.filter((a) => res.results[a])
  const extData: Row[] = EXT_ROWS.map(([metric, f]) => {
    const row: Row = { metric }
    for (const a of extAlgos) row[a] = f(res.results[a]!)
    return row
  })
  const before = previous?.res.results.dijkstra
  const now = res.results.dijkstra
  const moved = before?.status === 'ok' && now?.status === 'ok' && before.edge_ids?.join() !== now.edge_ids?.join()
  return (
    <VStack gap={3}>
      <HStack gap={2}>
        {algos.map((a) => <Badge key={a} variant={LEGEND[a]} label={ALGORITHM_LABEL[a]} />)}
      </HStack>
      {previous && (
        <VStack gap={0.5}>
          <Text type="body" weight="semibold">
            So với lần trước: {deltaText(costDelta(routeCost(previous.res), routeCost(res)))}
          </Text>
          <Text type="supporting">
            Lần trước: {previous.label}.{moved ? ' Tuyến lần trước vẽ nét xám mờ trên bản đồ.' : ''}
          </Text>
        </VStack>
      )}
      <Table<Row>
        data={data}
        idKey="metric"
        density="compact"
        columns={[
          { key: 'metric', header: 'Chỉ số' },
          ...algos.map((a) => ({ key: a, header: ALGORITHM_LABEL[a], align: 'end' as const })),
        ]}
      />
      <Text type="body" weight="semibold">{costLine(res)}</Text>
      {nodes && <Text type="body">{nodes}</Text>}
      <Text type="supporting">
        Thời gian tính là một lần chạy trên máy này, dao động giữa các lần; không dùng để so tốc độ hai thuật toán.
      </Text>
      <Text type="supporting">Kịch bản: {scenarioLabel}</Text>
      {extAlgos.length > 0 && (
        <VStack gap={2}>
          <Text type="body" weight="semibold">Phần mở rộng (ngoài proposal)</Text>
          <Table<Row>
            data={extData}
            idKey="metric"
            density="compact"
            columns={[
              { key: 'metric', header: 'Chỉ số' },
              // Cột hẹp: "Hai chiều" thay "Dijkstra hai chiều" để tiêu đề không bị cắt.
              ...extAlgos.map((a) => ({ key: a, header: a === 'bidijkstra' ? 'Hai chiều' : ALGORITHM_LABEL[a], align: 'end' as const })),
            ]}
          />
          <Text type="supporting">
            Cùng chi phí với Dijkstra: {extAlgos.every((a) => sameCost(res.results[a], res.results.dijkstra)) ? 'có' : 'không'}.
            Số đo trên nhiều cặp: EXPERIMENTS mục E2b.
          </Text>
        </VStack>
      )}
      {(res.warnings ?? []).map((w) => <Banner key={w} status="warning" title={w} />)}
    </VStack>
  )
}
