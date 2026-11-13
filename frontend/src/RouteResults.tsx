// Cột kết quả của chế độ tìm đường: bảng so sánh Dijkstra / A* (DEMO mục 1.3, nhãn bắt buộc ở mục 1.4).
import { Badge } from '@astryxdesign/core/Badge'
import { Banner } from '@astryxdesign/core/Banner'
import { HStack } from '@astryxdesign/core/HStack'
import { Table, proportional } from '@astryxdesign/core/Table'
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'
import { ALGORITHM_LABEL, type Algorithm, type AlgorithmResult, type RouteResponse } from './api'

const ALGOS: Algorithm[] = ['dijkstra', 'astar']
// Cùng màu với tuyến trên bản đồ (layers.ts: categorical blue / orange).
const LEGEND: Record<Algorithm, 'blue' | 'orange'> = { dijkstra: 'blue', astar: 'orange' }

export function num(x: number, digits = 1): string {
  return x.toLocaleString('vi-VN', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

// "Thời gian di chuyển ước tính" và "Thời gian tính toán" là hai nhãn tách riêng (DEMO mục 1.4).
// Giây là số chính; phút là dòng phụ để số chính đủ lớn khi chiếu máy chiếu.
export function secondsParts(s: number): { main: string; sub: string } {
  return { main: `${num(s)} s`, sub: `${num(s / 60)} phút` }
}

export function seconds(s: number): string {
  const { main, sub } = secondsParts(s)
  return `${main} (${sub})`
}

// Quãng đường: dưới 1 km giữ mét; từ 1 km hiển thị km (số chính) kèm mét chính xác (dòng phụ).
export function distanceParts(m: number): { main: string; sub?: string } {
  if (m < 1000) return { main: `${num(m, 0)} m` }
  return { main: `${num(m / 1000, 2)} km`, sub: `${num(m, 0)} m` }
}

interface Value {
  main: string
  sub?: string
}

interface Metric {
  id: string
  label: string
  hint?: string
  value: (r: AlgorithmResult) => Value
}

const METRICS: Metric[] = [
  {
    id: 'time',
    label: 'Thời gian di chuyển ước tính',
    hint: '(theo kịch bản)',
    value: (r) => (r.status === 'ok' && r.cost_s !== null ? secondsParts(r.cost_s) : { main: 'Không có đường' }),
  },
  {
    id: 'distance',
    label: 'Quãng đường',
    value: (r) => (r.status === 'ok' && r.distance_m !== null ? distanceParts(r.distance_m) : { main: '—' }),
  },
  {
    id: 'expanded',
    label: 'Số node mở rộng',
    value: (r) => ({ main: num(r.expanded, 0) }),
  },
  {
    id: 'runtime',
    label: 'Thời gian tính toán',
    value: (r) => ({ main: `${num(r.runtime_ms, 2)} ms` }),
  },
]

const METRIC_BY_ID = new Map(METRICS.map((m) => [m.id, m]))

interface Row extends Record<string, unknown> {
  id: string
  label: string
  hint?: string
}

// `trace_truncated` có trong contract backend nhưng chưa khai báo ở api.ts (file của agent khác):
// đọc phòng thủ, không sửa api.ts.
type WithTrace = AlgorithmResult & { trace_truncated?: boolean }

export default function RouteResults({ res, scenarioLabel }: { res: RouteResponse; scenarioLabel: string }) {
  const algos = ALGOS.filter((a) => res.results[a])
  const data: Row[] = METRICS.map((m) => {
    const row: Row = { id: m.id, label: m.label, hint: m.hint }
    for (const a of algos) row[a] = res.results[a]!
    return row
  })
  const noPath = algos.filter((a) => res.results[a]!.status === 'no_path')
  const truncated = algos.filter((a) => (res.results[a] as WithTrace).trace_truncated === true)
  const match = res.costs_match === true ? 'có' : res.costs_match === false ? 'không' : 'chưa rõ'

  const renderValue = (metricId: string, r: AlgorithmResult | undefined) => {
    const metric = METRIC_BY_ID.get(metricId)
    if (!r || !metric) return <Text type="body" justify="end">—</Text>
    const v = metric.value(r)
    return (
      <VStack gap={0.5} hAlign="end">
        <Text type="large" weight="semibold" hasTabularNumbers justify="end">{v.main}</Text>
        {v.sub && <Text type="supporting" hasTabularNumbers justify="end">{v.sub}</Text>}
      </VStack>
    )
  }

  return (
    <VStack gap={3} aria-live="polite">
      <HStack gap={2}>
        {algos.map((a) => <Badge key={a} variant={LEGEND[a]} label={ALGORITHM_LABEL[a]} />)}
      </HStack>

      {noPath.length > 0 && (
        <Banner
          status="warning"
          collapsible={false}
          title={noPath.length === algos.length
            ? 'Không có đường đi giữa hai điểm trong kịch bản hiện tại'
            : `${noPath.map((a) => ALGORITHM_LABEL[a]).join(', ')} không tìm thấy đường`}
          description="Bảng kết quả ghi nhận trạng thái không có đường; bản đồ không vẽ tuyến."
        />
      )}
      {truncated.length > 0 && (
        <Banner
          status="info"
          collapsible={false}
          title={`Danh sách node mở rộng của ${truncated.map((a) => ALGORITHM_LABEL[a]).join(', ')} đã bị cắt bớt`}
          description="Số node mở rộng vẫn là số đầy đủ; chỉ danh sách node chi tiết bị giới hạn bởi trace_limit."
        />
      )}

      <Table<Row>
        data={data}
        idKey="id"
        density="balanced"
        dividers="rows"
        aria-label="Bảng so sánh kết quả Dijkstra và A*"
        columns={[
          {
            key: 'label',
            header: 'Chỉ số',
            width: proportional(2),
            renderCell: (row) => (
              <VStack gap={0.5}>
                <Text type="body" weight="medium">{String(row.label)}</Text>
                {row.hint && <Text type="supporting">{String(row.hint)}</Text>}
              </VStack>
            ),
          },
          ...algos.map((a) => ({
            key: a,
            header: ALGORITHM_LABEL[a],
            align: 'end' as const,
            renderCell: (row: Row) => renderValue(String(row.id), row[a] as AlgorithmResult | undefined),
          })),
        ]}
      />

      <HStack gap={2} vAlign="center">
        <Text type="body" weight="semibold">Chi phí trùng khớp:</Text>
        <Badge
          variant={res.costs_match === true ? 'success' : res.costs_match === false ? 'error' : 'neutral'}
          label={match}
        />
      </HStack>
      {res.costs_match === false && (
        <Banner
          status="error"
          collapsible={false}
          title="Chi phí của Dijkstra và A* không trùng khớp"
          description="Hai thuật toán phải cho cùng chi phí tối ưu; chênh lệch nghĩa là dữ liệu hoặc kết quả cần kiểm tra lại."
        />
      )}

      <Text type="supporting">Kịch bản: {scenarioLabel}</Text>
      {(res.warnings ?? []).map((w) => <Banner key={w} status="warning" title={w} collapsible={false} />)}
    </VStack>
  )
}
