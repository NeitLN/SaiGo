// Cột kết quả của chế độ tour (T73; DEMO mục 1.3): 3 thẻ Thứ tự nhập / NN / NN + 2-opt. Chọn thẻ thì bản đồ
// vẽ tuyến và đánh số điểm giao theo thẻ đó.
import { Badge } from '@astryxdesign/core/Badge'
import { Banner } from '@astryxdesign/core/Banner'
import { Button } from '@astryxdesign/core/Button'
import { Card } from '@astryxdesign/core/Card'
import { HStack } from '@astryxdesign/core/HStack'
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'
import { TOUR_METHOD_LABEL, type TourMethod, type TourResponse } from './api'
import { num, seconds } from './RouteResults'
import { describeIssue, unreachableGroups } from './tourIssues'
import { costDelta, deltaText, orderChanged } from './compare'

/** Chi phí của phương án được chọn, hoặc null khi tour không khả thi. */
const chosenCost = (r: TourResponse): number | null =>
  r.status === 'ok' && r.chosen ? (r.candidates[r.chosen]?.cost_s ?? null) : null
const chosenStops = (r: TourResponse): string[] | null =>
  r.status === 'ok' && r.chosen ? (r.candidates[r.chosen]?.stop_order ?? null) : null

// kept_order chỉ có sau khi đóng đường (R1 C6): thứ tự cũ đi lại trên đường hiện tại, để so với việc sắp lại.
// optimal đứng cuối: thẻ đối chứng Held–Karp, cho xem tour tối ưu mà các heuristic phải so (review 14/11 đợt 2).
const METHODS: TourMethod[] = ['input', 'nearest_neighbor', 'nearest_neighbor_2opt', 'kept_order', 'optimal']

/** So với thứ tự nhập, không in "cải thiện" kèm số âm (review 14/11, AI-4). Ngưỡng 0,05% để khớp số in ra 1 chữ số. */
function improvementText(pct: number): string {
  if (Math.abs(pct) < 0.05) return 'Bằng thứ tự nhập'
  return pct > 0 ? `Rẻ hơn thứ tự nhập ${num(pct)}%` : `Đắt hơn thứ tự nhập ${num(-pct)}%`
}

export default function TourResults({ res, labels, selected, onSelect, scenarioLabel, previous }: {
  res: TourResponse
  labels: Record<string, string>
  selected: TourMethod | null
  onSelect: (m: TourMethod) => void
  scenarioLabel: string   // kịch bản của chính request đã trả về (QA-5), như dòng "Kịch bản" của RouteResults
  // Lần trước cùng bộ điểm, khác kịch bản hoặc cạnh đóng (review 14/11 đợt 2: PM-1, UX-5, AI-7).
  previous?: { res: TourResponse; label: string } | null
}) {
  const compareLine = previous && (
    <VStack gap={0.5}>
      <Text type="body" weight="semibold">
        So với lần trước, phương án được chọn: {deltaText(costDelta(chosenCost(previous.res), chosenCost(res)))}
      </Text>
      {orderChanged(chosenStops(previous.res), chosenStops(res)) && (
        <Text type="body">
          Thứ tự giao đã đổi, nên chênh lệch này gồm cả phần do sắp lại, không chỉ do kịch bản hay đường đóng.
          {res.candidates.kept_order ? ' Ảnh hưởng của riêng việc đóng đường: xem thẻ "Giữ thứ tự cũ".' : ''}
        </Text>
      )}
      <Text type="supporting">Lần trước: {previous.label}.</Text>
    </VStack>
  )
  // Cùng thứ tự với "Giữ thứ tự cũ" ở lần trước (thường là phương án đang xem lúc bấm đóng đường): so được
  // trực tiếp "đóng đường làm tour này dài thêm bao nhiêu".
  const keptBefore = (order: string[]) => {
    if (!previous || previous.res.status !== 'ok') return null
    const key = order.join(',')
    const cands = Object.values(previous.res.candidates).filter((c) => c !== undefined)
    return cands.find((c) => c.stop_order.join(',') === key)?.cost_s ?? null
  }
  const name = (id: string) => {
    const label = labels[id] ?? id
    return id === 'depot' ? (label === 'Kho' ? 'kho' : `kho ${label}`) : label
  }
  if (res.status === 'infeasible_under_model') {
    const others = Object.keys(res.snapped).length - 1   // số điểm khác một điểm cho trước (gồm kho)
    return (
      <VStack gap={3}>
        {compareLine}
        <Banner status="error" title="Không lập được tour đầy đủ" collapsible={false}
          description="Có chặng không đi được trong kịch bản này, nên không hiện tour thiếu điểm. Điểm hỏng được tô đỏ trên bản đồ.">
          <VStack gap={1}>
            {unreachableGroups(res.unreachable).map((g) => (
              <Text key={g.id} type="body" weight="semibold">{describeIssue(g, others, name)}</Text>
            ))}
          </VStack>
        </Banner>
        <Text type="supporting">Kịch bản: {scenarioLabel}</Text>
      </VStack>
    )
  }
  // Sau khi đóng đường, "Giữ thứ tự cũ" đứng đầu để so ngay với việc sắp lại; trước đây nó rơi xuống dưới mép
  // màn hình (review 14/11, PM-5, UX-8).
  const methods = res.candidates.kept_order ? ['kept_order' as const, ...METHODS.filter((m) => m !== 'kept_order')] : METHODS
  // Badge cho mọi phương án rẻ nhất, kể cả khi hòa (AI-6); trước đây chỉ `chosen` có badge.
  const shown = methods.map((m) => res.candidates[m]).filter((c) => c !== undefined)
  const best = Math.min(...shown.map((c) => c.cost_s))
  const isCheapest = (cost: number) => cost <= best + 1e-6 * Math.max(1, best)
  const chosenOrder = res.chosen ? res.candidates[res.chosen]?.stop_order.join(',') : undefined
  return (
    <VStack gap={3}>
      {compareLine}
      {methods.map((m) => {
        const c = res.candidates[m]
        if (!c) return null
        const isSelected = m === selected
        return (
          <Card key={m} variant={isSelected ? 'blue' : 'default'} padding={3}>
            <VStack gap={1.5}>
              <HStack gap={2} hAlign="between" vAlign="center">
                <Text type="body" weight="semibold">{TOUR_METHOD_LABEL[m]}</Text>
                {isCheapest(c.cost_s) && <Badge variant="success" label="Rẻ nhất" />}
              </HStack>
              <Text type="body">Thời gian di chuyển ước tính: {seconds(c.cost_s)}</Text>
              <Text type="body">Quãng đường: {num(c.distance_m, 0)} m</Text>
              {m === 'kept_order' && (
                <Text type="supporting">Thứ tự trước khi đóng đường, mỗi chặng tìm lại trên đường hiện tại.</Text>
              )}
              {m === 'optimal' && (
                <Text type="supporting">
                  Quy hoạch động Held–Karp, chỉ tính khi tối đa 10 điểm giao. Dùng để đo các heuristic cách tối ưu bao xa,
                  không dùng để chọn tour.
                </Text>
              )}
              {m === 'kept_order' && keptBefore(c.stop_order) !== null && (
                <Text type="body" weight="semibold">
                  Cùng thứ tự, trước khi đóng: {deltaText(costDelta(keptBefore(c.stop_order), c.cost_s))}
                </Text>
              )}
              {m === 'kept_order' && c.stop_order.join(',') === chosenOrder && (
                <Text type="body">Sắp lại cho ra đúng thứ tự này: đóng đường không làm đổi thứ tự.</Text>
              )}
              {m !== 'input' && <Text type="body">{improvementText(c.improvement_pct)}</Text>}
              <Text type="supporting">Thứ tự: {c.stop_order.map(name).join(' → ')}</Text>
              <Button label={isSelected ? 'Đang hiển thị' : 'Xem trên bản đồ'} size="sm"
                variant={isSelected ? 'primary' : 'secondary'} onClick={() => onSelect(m)} />
            </VStack>
          </Card>
        )
      })}
      {res.optimal && (
        <Text type="supporting">
          Tối ưu (Held–Karp): {seconds(res.optimal.cost_s)};{' '}
          {res.optimal.gap_pct < 0.05
            ? 'phương án được chọn là tối ưu'
            : `phương án được chọn đắt hơn tối ưu ${num(res.optimal.gap_pct)}%`}
        </Text>
      )}
      <Text type="supporting">
        Thời gian tính toán: ma trận {num(res.matrix_runtime_ms, 2)} ms, sắp thứ tự {num(res.order_runtime_ms ?? 0, 2)} ms
      </Text>
      <Text type="supporting">Kịch bản: {scenarioLabel}</Text>
    </VStack>
  )
}
