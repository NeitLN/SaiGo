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

const METHODS: TourMethod[] = ['input', 'nearest_neighbor', 'nearest_neighbor_2opt']

export default function TourResults({ res, labels, selected, onSelect }: {
  res: TourResponse
  labels: Record<string, string>
  selected: TourMethod | null
  onSelect: (m: TourMethod) => void
}) {
  const name = (id: string) => labels[id] ?? id
  if (res.status === 'infeasible_under_model') {
    return (
      <Banner status="error" title="Không lập được tour đầy đủ" collapsible={false}
        description="Có chặng không đi được trong kịch bản này, nên không hiện tour thiếu điểm.">
        <VStack gap={1}>
          {res.unreachable.map((p) => (
            <Text key={`${p.from_id}-${p.to_id}`} type="body">Không đi được: {name(p.from_id)} → {name(p.to_id)}</Text>
          ))}
        </VStack>
      </Banner>
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
    </VStack>
  )
}
