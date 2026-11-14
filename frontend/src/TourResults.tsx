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

// kept_order chỉ có sau khi đóng đường (R1 C6): thứ tự cũ đi lại trên đường hiện tại, để so với việc sắp lại.
const METHODS: TourMethod[] = ['input', 'nearest_neighbor', 'nearest_neighbor_2opt', 'kept_order']

type Pair = { from_id: string; to_id: string }
export interface UnreachableGroup { id: string; dir: 'to' | 'from'; others: string[] }

/**
 * Gom các cặp không đi được (R1 C4) thành ít dòng nhất (review 14/11, QA-14): gom theo điểm đến hoặc theo
 * điểm đi, cách nào ra ít nhóm hơn. Một điểm bị cô lập thường là đích của mọi cặp hỏng, nên chỉ còn một dòng
 * thay cho n dòng "Không đi được: X → Y". `id` của mỗi nhóm là điểm cần tô đỏ trên bản đồ.
 */
export function unreachableGroups(pairs: Pair[]): UnreachableGroup[] {
  const group = (key: (p: Pair) => string, other: (p: Pair) => string) => {
    const m = new Map<string, string[]>()
    for (const p of pairs) m.set(key(p), [...(m.get(key(p)) ?? []), other(p)])
    return m
  }
  const byTo = group((p) => p.to_id, (p) => p.from_id)
  const byFrom = group((p) => p.from_id, (p) => p.to_id)
  return byTo.size <= byFrom.size
    ? [...byTo].map(([id, others]) => ({ id, dir: 'to' as const, others }))
    : [...byFrom].map(([id, others]) => ({ id, dir: 'from' as const, others }))
}

export default function TourResults({ res, labels, selected, onSelect, scenarioLabel }: {
  res: TourResponse
  labels: Record<string, string>
  selected: TourMethod | null
  onSelect: (m: TourMethod) => void
  scenarioLabel: string   // kịch bản của chính request đã trả về (QA-5), như dòng "Kịch bản" của RouteResults
}) {
  const name = (id: string) => {
    const label = labels[id] ?? id
    return id === 'depot' ? (label === 'Kho' ? 'kho' : `kho ${label}`) : label
  }
  if (res.status === 'infeasible_under_model') {
    const others = Object.keys(res.snapped).length - 1   // số điểm khác một điểm cho trước (gồm kho)
    const line = (g: UnreachableGroup) => {
      const all = g.others.length === others
      if (g.dir === 'to') {
        return all ? `Không điểm nào đi tới được ${name(g.id)}.` : `Không đi tới được ${name(g.id)} từ: ${g.others.map(name).join(', ')}.`
      }
      return all ? `Từ ${name(g.id)} không đi được tới điểm nào.` : `Từ ${name(g.id)} không đi tới được: ${g.others.map(name).join(', ')}.`
    }
    return (
      <VStack gap={3}>
        <Banner status="error" title="Không lập được tour đầy đủ" collapsible={false}
          description="Có chặng không đi được trong kịch bản này, nên không hiện tour thiếu điểm. Điểm hỏng được tô đỏ trên bản đồ.">
          <VStack gap={1}>
            {unreachableGroups(res.unreachable).map((g) => (
              <Text key={`${g.dir}-${g.id}`} type="body" weight="semibold">{line(g)}</Text>
            ))}
          </VStack>
        </Banner>
        <Text type="supporting">Kịch bản: {scenarioLabel}</Text>
      </VStack>
    )
  }
  return (
    <VStack gap={3}>
      {METHODS.map((m) => {
        const c = res.candidates[m]
        if (!c) return null
        const isSelected = m === selected
        return (
          <Card key={m} variant={isSelected ? 'blue' : 'default'} padding={3}>
            <VStack gap={1.5}>
              <HStack gap={2} hAlign="between" vAlign="center">
                <Text type="body" weight="semibold">{TOUR_METHOD_LABEL[m]}</Text>
                {m === res.chosen && <Badge variant="success" label="Rẻ nhất" />}
              </HStack>
              <Text type="body">Thời gian di chuyển ước tính: {seconds(c.cost_s)}</Text>
              <Text type="body">Quãng đường: {num(c.distance_m, 0)} m</Text>
              {m === 'kept_order' && (
                <Text type="supporting">Thứ tự trước khi đóng đường, mỗi chặng tìm lại trên đường hiện tại.</Text>
              )}
              {m !== 'input' && <Text type="body">Cải thiện so với thứ tự nhập: {num(c.improvement_pct)}%</Text>}
              <Text type="supporting">Thứ tự: {c.stop_order.map(name).join(' → ')}</Text>
              <Button label={isSelected ? 'Đang hiển thị' : 'Xem trên bản đồ'} size="sm"
                variant={isSelected ? 'primary' : 'secondary'} onClick={() => onSelect(m)} />
            </VStack>
          </Card>
        )
      })}
      {res.optimal && (
        <Text type="supporting">
          Tối ưu (Held–Karp): {seconds(res.optimal.cost_s)}; phương án được chọn cách tối ưu {num(res.optimal.gap_pct)}%
        </Text>
      )}
      <Text type="supporting">
        Thời gian tính toán: ma trận {num(res.matrix_runtime_ms, 2)} ms, sắp thứ tự {num(res.order_runtime_ms ?? 0, 2)} ms
      </Text>
      <Text type="supporting">Kịch bản: {scenarioLabel}</Text>
    </VStack>
  )
}
