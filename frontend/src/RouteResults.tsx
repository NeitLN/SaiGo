// Cột kết quả của chế độ tìm đường: bảng so sánh Dijkstra / A* (DEMO mục 1.3, nhãn bắt buộc ở mục 1.4).
import { Badge } from '@astryxdesign/core/Badge'
import { Banner } from '@astryxdesign/core/Banner'
import { HStack } from '@astryxdesign/core/HStack'
import { Table } from '@astryxdesign/core/Table'
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'
import { ALGORITHM_LABEL, type Algorithm, type AlgorithmResult, type RouteResponse } from './api'

const ALGOS: Algorithm[] = ['dijkstra', 'astar']
// Cùng màu với tuyến trên bản đồ (layers.ts: categorical blue / orange).
const LEGEND: Record<Algorithm, 'blue' | 'orange'> = { dijkstra: 'blue', astar: 'orange' }

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
  ['Thời gian tính toán', (r) => `${num(r.runtime_ms, 2)} ms`],
]

interface Row extends Record<string, unknown> {
  metric: string
  dijkstra?: string
  astar?: string
}

export default function RouteResults({ res, scenarioLabel }: { res: RouteResponse; scenarioLabel: string }) {
  const algos = ALGOS.filter((a) => res.results[a])
  const data: Row[] = ROWS.map(([metric, f]) => {
    const row: Row = { metric }
    for (const a of algos) row[a] = f(res.results[a]!)
    return row
  })
  const match = res.costs_match === true ? 'có' : res.costs_match === false ? 'không' : '—'
  return (
    <VStack gap={3}>
      <HStack gap={2}>
        {algos.map((a) => <Badge key={a} variant={LEGEND[a]} label={ALGORITHM_LABEL[a]} />)}
      </HStack>
      <Table<Row>
        data={data}
        idKey="metric"
        density="compact"
        columns={[
          { key: 'metric', header: '' },
          ...algos.map((a) => ({ key: a, header: ALGORITHM_LABEL[a], align: 'end' as const })),
        ]}
      />
      <Text type="body" weight="semibold">Chi phí trùng khớp: {match}</Text>
      <Text type="supporting">Kịch bản: {scenarioLabel}</Text>
      {(res.warnings ?? []).map((w) => <Banner key={w} status="warning" title={w} />)}
    </VStack>
  )
}
