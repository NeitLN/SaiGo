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
import { distanceParts, num, seconds, secondsParts } from './RouteResults'

const METHODS: TourMethod[] = ['input', 'nearest_neighbor', 'nearest_neighbor_2opt']

export default function TourResults({ res, labels, selected, onSelect }: {
  res: TourResponse
  labels: Record<string, string>
  selected: TourMethod | null
  onSelect: (m: TourMethod) => void
}) {
  const name = (id: string) => labels[id] ?? id
  const warnings = (res.warnings ?? []).map((w) => (
    <Banner key={w} status="warning" title={w} collapsible={false} />
  ))

  if (res.status === 'infeasible_under_model') {
    return (
      <VStack gap={3} aria-live="polite">
        <Banner status="error" title="Không lập được tour đầy đủ" collapsible={false}
          description="Có chặng không đi được trong kịch bản này, nên không hiện tour thiếu điểm. Các cặp điểm dưới đây không nối được:">
          <VStack gap={1}>
            {res.unreachable.map((p) => (
              <Text key={`${p.from_id}-${p.to_id}`} type="body">Không đi được: {name(p.from_id)} → {name(p.to_id)}</Text>
            ))}
          </VStack>
        </Banner>
        {warnings}
      </VStack>
    )
  }

  const missing = METHODS.filter((m) => !res.candidates[m])

  return (
    <VStack gap={3} aria-live="polite">
      {missing.length > 0 && (
        <Banner status="info" collapsible={false}
          title="Thiếu kết quả của một số phương pháp"
          description={`API không trả về: ${missing.map((m) => TOUR_METHOD_LABEL[m]).join(', ')}.`} />
      )}
      {res.chosen === null && (
        <Banner status="warning" collapsible={false}
          title="Chưa có phương án nào được chọn"
          description="API không trả về phương án rẻ nhất; bấm “Xem trên bản đồ” ở một thẻ để vẽ tuyến." />
      )}

      {METHODS.map((m) => {
        const c = res.candidates[m]
        if (!c) return null
        const isSelected = m === selected
        const time = secondsParts(c.cost_s)
        const distance = distanceParts(c.distance_m)
        return (
          <Card key={m} variant={isSelected ? 'blue' : 'default'} padding={3}>
            <VStack gap={1.5}>
              <HStack gap={2} hAlign="between" vAlign="start">
                <Text type="large" weight="semibold" as="h3">{TOUR_METHOD_LABEL[m]}</Text>
                <HStack gap={1} vAlign="center">
                  {m === res.chosen && <Badge variant="success" label="Rẻ nhất" />}
                  {isSelected && <Badge variant="info" label="Đang xem" />}
                </HStack>
              </HStack>

              <VStack gap={0.5}>
                <Text type="supporting">Thời gian di chuyển ước tính</Text>
                <HStack gap={2} vAlign="end">
                  <Text type="large" weight="semibold" hasTabularNumbers>{time.main}</Text>
                  <Text type="body" hasTabularNumbers>{time.sub}</Text>
                </HStack>
              </VStack>
              <VStack gap={0.5}>
                <Text type="supporting">Quãng đường</Text>
                <HStack gap={2} vAlign="end">
                  <Text type="large" weight="semibold" hasTabularNumbers>{distance.main}</Text>
                  {distance.sub && <Text type="body" hasTabularNumbers>{distance.sub}</Text>}
                </HStack>
              </VStack>

              {m !== 'input' && (
                <Text type="body">Cải thiện so với thứ tự nhập: {num(c.improvement_pct)}%</Text>
              )}
              <Text type="body">Thứ tự giao: {c.stop_order.map(name).join(' → ')}</Text>
              <Button size="sm"
                label={isSelected ? 'Đang hiển thị' : 'Xem trên bản đồ'}
                aria-label={`${isSelected ? 'Đang hiển thị' : 'Xem'} tour ${TOUR_METHOD_LABEL[m]} trên bản đồ`}
                aria-pressed={isSelected}
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
      <Text type="supporting">Thời gian tính toán ma trận: {num(res.matrix_runtime_ms, 2)} ms</Text>
      <Text type="supporting">Thời gian sắp thứ tự: {num(res.order_runtime_ms ?? 0, 2)} ms</Text>
      {warnings}
    </VStack>
  )
}
