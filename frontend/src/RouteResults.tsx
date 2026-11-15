// Cột kết quả của chế độ tìm đường: bảng so sánh Dijkstra / A* (DEMO mục 1.3, nhãn bắt buộc ở mục 1.4).
import { Badge } from '@astryxdesign/core/Badge'
import { Banner } from '@astryxdesign/core/Banner'
import { HStack } from '@astryxdesign/core/HStack'
import { StackItem } from '@astryxdesign/core/Stack'
import { Table } from '@astryxdesign/core/Table'
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'
import { ALGORITHM_LABEL, type Algorithm, type AlgorithmResult, type RouteResponse } from './api'
import { costDelta, deltaText } from './compare'
import { Grid } from '@astryxdesign/core/Grid'
import { ProgressBar } from '@astryxdesign/core/ProgressBar'
import Kpi, { km, metersRaw, minutes, secondsRaw } from './Kpi'

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
  ['Thời gian di chuyển ước tính (theo điều kiện giao thông)', (r) => (r.status !== 'ok' || r.cost_s === null ? 'Không có đường' : seconds(r.cost_s))],
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

/**
 * Số node mở rộng bằng thanh ngang cùng trục 0 → số node của đồ thị (đợt UI "Bàn điều phối", RQ1): độ dài thanh so
 * được giữa các lần chạy. Số in cạnh thanh nên không chỉ dựa vào độ dài hay màu. Màu thanh trùng màu chấm node trên
 * bản đồ (Dijkstra xám, A* cam).
 */
function NodeBars({ res, nodeCount }: { res: RouteResponse; nodeCount?: number }) {
  const rows = ALGOS.filter((a) => res.results[a]).map((a) => ({ a, n: res.results[a]!.expanded }))
  if (!rows.length) return null
  const total = nodeCount && nodeCount > 0 ? nodeCount : Math.max(...rows.map((r) => r.n), 1)
  const d = res.results.dijkstra
  const a = res.results.astar
  const both = d?.status === 'ok' && a?.status === 'ok' && d.expanded > 0
  const none = d?.status === 'no_path' && a?.status === 'no_path'
  return (
    <VStack gap={2}>
      <Text type="body" weight="semibold">
        Node đã mở rộng{nodeCount ? ` (trên ${num(nodeCount, 0)} node của đồ thị)` : ''}
      </Text>
      {rows.map(({ a: algo, n }) => (
        <HStack key={algo} gap={3} vAlign="center">
          <VStack width={72}><Text type="body" weight="semibold">{ALGORITHM_LABEL[algo]}</Text></VStack>
          <StackItem size="fill">
            <VStack className={`node-bar node-bar-${algo}`}>
              <ProgressBar label={`${ALGORITHM_LABEL[algo]}: ${num(n, 0)} node đã mở rộng`} isLabelHidden value={n} max={total}
                variant="neutral" />
            </VStack>
          </StackItem>
          <VStack width={136} hAlign="end">
            <Text type="body" hasTabularNumbers textWrap="nowrap">
              <Text type="large" weight="bold" hasTabularNumbers>{num(n, 0)}</Text> node
              {nodeCount ? ` · ${num((100 * n) / total, 1)}%` : ''}
            </Text>
          </VStack>
        </HStack>
      ))}
      {both && (
        <Text type="body">
          A* mở ít hơn <Text type="inherit" weight="bold">{num(100 * (1 - a.expanded / d.expanded), 1)}%</Text> node so với Dijkstra
          {res.costs_match ? ' mà vẫn ra cùng chi phí.' : '.'}
        </Text>
      )}
      {none && <Text type="body">Không có đường: cả hai thuật toán duyệt hết phần đồ thị đi tới được rồi dừng.</Text>}
    </VStack>
  )
}

export default function RouteResults({ res, scenarioLabel, previous, hasSummary = false, nodeCount }: {
  res: RouteResponse
  // Số node của đồ thị (/api/dataset), làm trục cho thanh node; không có thì trục theo thuật toán mở nhiều nhất.
  nodeCount?: number
  // Đợt UI "Bàn điều phối": ô số chính đã ở dải tóm tắt đầu panel trái, khay phân tích không lặp lại.
  hasSummary?: boolean
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
  // Cùng điều kiện với App khi vẽ tuyến lần trước (test lại 15/11, R-4): cả khi lần này không còn đường.
  const moved = before?.status === 'ok' && (now?.status !== 'ok' || before.edge_ids?.join() !== now.edge_ids?.join())
  const lost = before?.status === 'ok' && now?.status !== 'ok'
  // Ô số chính (đợt UI 15/11): thời gian và quãng đường của tuyến Dijkstra (A* cho cùng chi phí khi "Chi phí trùng
  // khớp: có"). Khi hai thuật toán cùng chi phí thì hai dòng đó không lặp lại trong bảng so sánh bên dưới.
  const ok = now?.status === 'ok' && now.cost_s !== null
  const same = res.costs_match === true
  const tableData = ok && same ? data.slice(2) : data
  return (
    <VStack gap={3}>
      {ok ? (hasSummary ? null : (
        <Grid columns={2} gap={2}>
          <Kpi label="Thời gian di chuyển ước tính" value={minutes(now.cost_s!)}
            sub={`theo điều kiện giao thông · ${secondsRaw(now.cost_s!)}${same ? '' : ' · theo Dijkstra'}`} />
          <Kpi label="Quãng đường" value={km(now.distance_m ?? 0)} sub={metersRaw(now.distance_m ?? 0)} />
        </Grid>
      )) : (
        <Kpi label="Thời gian di chuyển ước tính" value="Không có đường"
          sub="Không còn đường đi giữa hai điểm với điều kiện giao thông này." />
      )}
      {previous && (
        <VStack gap={0.5}>
          {!hasSummary && (
            <Text type="body" weight="semibold">
              So với lần trước: {deltaText(costDelta(routeCost(previous.res), routeCost(res)))}
            </Text>
          )}
          <Text type="supporting">
            {/* Ghi cả hai kịch bản (R-7): so với lần ngay trước, không phải với Cơ sở. */}
            Lần trước: {previous.label}. Lần này: {scenarioLabel}.
            {lost ? ' Nét rỗng màu xám trên bản đồ là tuyến lần trước, nay không đi được.' : moved ? ' Tuyến lần trước vẽ nét rỗng màu xám trên bản đồ.' : ''}
          </Text>
        </VStack>
      )}
      {hasSummary && (
        <HStack gap={6} vAlign="start" wrap="wrap">
          <VStack style={{ flex: '1 1 340px', minWidth: 0 }}><NodeBars res={res} nodeCount={nodeCount} /></VStack>
          <VStack gap={2} style={{ flex: '0 1 220px' }}>
            <Text type="body" weight="semibold">Chi phí trùng khớp</Text>
            {res.costs_match === true && ok ? (
              <HStack gap={2} vAlign="center">
                <Badge variant="success" label="Có" />
                <Text type="body" hasTabularNumbers>Cùng {secondsRaw(now.cost_s!)} · {metersRaw(now.distance_m ?? 0)}</Text>
              </HStack>
            ) : (
              <Text type="body">{costLine(res)}</Text>
            )}
          </VStack>
          <VStack gap={2} style={{ flex: '0 1 200px' }}>
            <Text type="body" weight="semibold">Thời gian tính toán (1 lần chạy)</Text>
            {algos.map((a) => (
              <HStack key={a} gap={2} hAlign="between">
                <Text type="body">{ALGORITHM_LABEL[a]}</Text>
                <Text type="body" hasTabularNumbers>{num(res.results[a]!.runtime_ms, 2)} ms</Text>
              </HStack>
            ))}
            <Text type="supporting">Một lần chạy trên máy này, dao động giữa các lần; không dùng để so tốc độ.</Text>
          </VStack>
        </HStack>
      )}
      {(!hasSummary || (ok && !same)) && (<>
      <HStack gap={2} vAlign="center" hAlign="between">
        <Text type="body" weight="semibold">So sánh thuật toán</Text>
        <HStack gap={1}>
          {algos.map((a) => <Badge key={a} variant={LEGEND[a]} label={ALGORITHM_LABEL[a]} />)}
        </HStack>
      </HStack>
      <Table<Row>
        data={tableData}
        idKey="metric"
        density="compact"
        columns={[
          { key: 'metric', header: 'Chỉ số' },
          ...algos.map((a) => ({ key: a, header: ALGORITHM_LABEL[a], align: 'end' as const })),
        ]}
      />
      {!hasSummary && <Text type="body" weight="semibold">{costLine(res)}</Text>}
      {!hasSummary && nodes && <Text type="body">{nodes}</Text>}
      {!hasSummary && (
        <Text type="supporting">
          Thời gian tính là một lần chạy trên máy này, dao động giữa các lần; không dùng để so tốc độ hai thuật toán.
        </Text>
      )}
      </>)}
      {!hasSummary && <Text type="supporting">Điều kiện giao thông: {scenarioLabel}</Text>}
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
            {/* Cả bốn cùng không có đường thì không gọi là "cùng chi phí" (R-3), như dòng của bảng chính. */}
            {extAlgos.every((a) => res.results[a]?.status === 'no_path') && res.results.dijkstra?.status === 'no_path'
              ? 'Cả bốn thuật toán cùng báo không có đường.'
              : `Cùng chi phí với Dijkstra: ${extAlgos.every((a) => sameCost(res.results[a], res.results.dijkstra)) ? 'có' : 'không'}.`}
            {' '}Số đo trên nhiều cặp điểm nằm ở phần thí nghiệm của báo cáo.
          </Text>
        </VStack>
      )}
      {(res.warnings ?? []).map((w) => <Banner key={w} status="warning" title={w} />)}
    </VStack>
  )
}
