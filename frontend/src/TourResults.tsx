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
import { Grid } from '@astryxdesign/core/Grid'
import Kpi, { km, kmText, metersRaw, minutes, minutesText, secondsRaw } from './Kpi'

/** Chi phí của phương án được chọn, hoặc null khi tour không khả thi. */
const chosenCost = (r: TourResponse): number | null =>
  r.status === 'ok' && r.chosen ? (r.candidates[r.chosen]?.cost_s ?? null) : null
const chosenStops = (r: TourResponse): string[] | null =>
  r.status === 'ok' && r.chosen ? (r.candidates[r.chosen]?.stop_order ?? null) : null

// kept_order chỉ có sau khi đóng đường (R1 C6): thứ tự cũ đi lại trên đường hiện tại, để so với việc sắp lại.
// optimal đứng cuối: thẻ đối chứng Held–Karp, cho xem tour tối ưu mà các heuristic phải so (review 14/11 đợt 2).
// nearest_neighbor_2opt_oropt chỉ có khi bật "Phần mở rộng" (đợt 3); đứng trước thẻ tối ưu.
const METHODS: TourMethod[] = [
  'input', 'nearest_neighbor', 'nearest_neighbor_2opt', 'kept_order', 'nearest_neighbor_2opt_oropt', 'optimal',
]

/** So với thứ tự nhập, không in "cải thiện" kèm số âm (review 14/11, AI-4). Ngưỡng 0,05% để khớp số in ra 1 chữ số. */
function improvementText(pct: number): string {
  if (Math.abs(pct) < 0.05) return 'Bằng thứ tự nhập'
  // "Nhanh hơn / chậm hơn" thay "rẻ / đắt": đại lượng là thời gian, không phải tiền (đợt UI 15/11).
  return pct > 0 ? `Nhanh hơn thứ tự nhập ${num(pct)}%` : `Chậm hơn thứ tự nhập ${num(-pct)}%`
}

export default function TourResults({ res, labels, selected, onSelect, scenarioLabel, previous, hasSummary = false }: {
  res: TourResponse
  // Ô số chính đã ở dải tóm tắt đầu panel trái (đợt UI "Bàn điều phối"), thẻ "Đang xem" không lặp lại.
  hasSummary?: boolean
  labels: Record<string, string>
  selected: TourMethod | null
  onSelect: (m: TourMethod) => void
  scenarioLabel: string   // kịch bản của chính request đã trả về (QA-5), như dòng "Kịch bản" của RouteResults
  // Lần trước cùng bộ điểm, khác kịch bản hoặc cạnh đóng (review 14/11 đợt 2: PM-1, UX-5, AI-7).
  // closedMore: lần trước cùng kịch bản và lần này chỉ đóng thêm đoạn; chỉ khi đó mới so "Cùng thứ tự, trước khi
  // đóng" (test lại 15/11, T-1: đổi kịch bản sau khi đóng từng làm dòng này gán phần chênh do cao điểm cho việc đóng).
  previous?: { res: TourResponse; label: string; closedMore: boolean } | null
}) {
  const compareLine = previous && (
    <VStack gap={0.5}>
      <Text type="body" weight="semibold">
        So với lần trước, phương án được chọn: {deltaText(costDelta(chosenCost(previous.res), chosenCost(res)), 'tour')}
      </Text>
      {orderChanged(chosenStops(previous.res), chosenStops(res)) && (
        <Text type="body">
          Thứ tự giao đã đổi, nên chênh lệch này gồm cả phần do sắp lại, không chỉ do điều kiện giao thông hay đường đóng.
          {res.candidates.kept_order ? ' Ảnh hưởng của riêng việc đóng đường: xem thẻ "Giữ thứ tự cũ".' : ''}
        </Text>
      )}
      <Text type="supporting">Lần trước: {previous.label}. Lần này: {scenarioLabel}.</Text>
    </VStack>
  )
  // Cùng thứ tự với "Giữ thứ tự cũ" ở lần trước (thường là phương án đang xem lúc bấm đóng đường): so được
  // trực tiếp "đóng đường làm tour này dài thêm bao nhiêu".
  const keptBefore = (order: string[]) => {
    if (!previous || !previous.closedMore || previous.res.status !== 'ok') return null
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
          description="Có chặng không đi được với điều kiện giao thông này, nên không hiện tour thiếu điểm. Điểm hỏng được tô đỏ trên bản đồ.">
          <VStack gap={1}>
            {unreachableGroups(res.unreachable).map((g) => (
              <Text key={g.id} type="body" weight="semibold">{describeIssue(g, others, name)}</Text>
            ))}
          </VStack>
        </Banner>
        <Text type="supporting">Điều kiện giao thông: {scenarioLabel}</Text>
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
  // Đợt UI 15/11 (họp thiết kế 5 vai): tour đọc như một chuyến giao. Phương án đang xem lên đầu: ô số chính (phút, km)
  // và lịch trình Kho → 1 … n → về kho, đánh số khớp marker. Các phương án khác thành danh sách so sánh gọn, vẫn bấm
  // "Xem trên bản đồ". Số của phương án đang xem, không phải lúc nào cũng là phương án được chọn (vd. Held–Karp).
  const viewKey = selected && res.candidates[selected] ? selected : res.chosen
  const view = viewKey ? res.candidates[viewKey] : undefined
  const depotName = labels.depot && labels.depot !== 'Kho' ? labels.depot : 'Kho'
  const note = (m: TourMethod, c: NonNullable<typeof view>) => (
    <>
      {m === 'kept_order' && (
        <Text type="supporting">Thứ tự trước khi đóng đường, mỗi chặng tìm lại trên đường hiện tại.</Text>
      )}
      {m === 'nearest_neighbor_2opt_oropt' && (
        <Text type="supporting">
          Phần mở rộng: Or-opt xen kẽ 2-opt, chạy tiếp từ NN + 2-opt. Không nằm trong các phương án đã đo ở E5,
          nên không có số đo tổng quát; không dùng để chọn tour.
        </Text>
      )}
      {m === 'optimal' && (
        <Text type="supporting">
          Quy hoạch động Held–Karp, chỉ tính khi tối đa 10 điểm giao. Dùng để đo các heuristic cách tối ưu bao xa,
          không dùng để chọn tour.
        </Text>
      )}
      {m === 'kept_order' && keptBefore(c.stop_order) !== null && (
        <Text type="body" weight="semibold">
          Cùng thứ tự, trước khi đóng: {deltaText(costDelta(keptBefore(c.stop_order), c.cost_s), 'tour')}
        </Text>
      )}
      {m === 'kept_order' && c.stop_order.join(',') === chosenOrder && (
        <Text type="body">Sắp lại cho ra đúng thứ tự này: đóng đường không làm đổi thứ tự.</Text>
      )}
    </>
  )
  return (
    <VStack gap={3}>
      {view && viewKey && (
        <Card padding={3} elevation="low">
          <VStack gap={2}>
            <HStack gap={2} hAlign="between" vAlign="center">
              <Text type="body" weight="semibold">Đang xem: {TOUR_METHOD_LABEL[viewKey]}</Text>
              <HStack gap={1}>
                {viewKey === res.chosen && <Badge variant="purple" label="Được chọn" />}
                {viewKey === 'optimal' && <Badge variant="neutral" label="Đối chứng" />}
              </HStack>
            </HStack>
            {!hasSummary && (
              <Grid columns={2} gap={2}>
                <Kpi label="Thời gian di chuyển ước tính" value={minutes(view.cost_s)} sub={secondsRaw(view.cost_s)} />
                <Kpi label="Quãng đường" value={km(view.distance_m)} sub={metersRaw(view.distance_m)} />
              </Grid>
            )}
            <Text type="supporting">
              {view.stop_order.length} điểm giao · gồm chặng về kho
              {viewKey !== 'input' ? ` · ${improvementText(view.improvement_pct).toLowerCase()}` : ''}
            </Text>
            {/* Lịch trình: số khớp marker trên bản đồ. Không có giờ đến từng điểm: API chỉ trả tổng của cả tour. */}
            <VStack gap={1}>
              <HStack gap={2} vAlign="center">
                <Badge variant="green" label="K" />
                <Text type="body">{depotName}</Text>
              </HStack>
              {view.stop_order.map((id, i) => (
                <HStack key={id} gap={2} vAlign="center">
                  <Badge variant="purple" label={String(i + 1)} />
                  <Text type="body">{name(id)}</Text>
                </HStack>
              ))}
              <HStack gap={2} vAlign="center">
                <Badge variant="green" label="K" />
                <Text type="supporting">Về {depotName === 'Kho' ? 'kho' : depotName}</Text>
              </HStack>
            </VStack>
            {note(viewKey, view)}
          </VStack>
        </Card>
      )}
      {compareLine}
      <Text type="body" weight="semibold">Các phương án</Text>
      {methods.map((m) => {
        const c = res.candidates[m]
        if (!c) return null
        const isSelected = m === selected
        return (
          <Card key={m} padding={2} variant={isSelected ? 'muted' : 'default'}>
            <VStack gap={1}>
              <Text type="body" weight="semibold">{TOUR_METHOD_LABEL[m]}</Text>
              {/* Badge dòng riêng: cùng hàng với tên dài (Held–Karp) thì bị cắt ở cột 360 px (góp ý #160). */}
              {isCheapest(c.cost_s) && <HStack><Badge variant="success" label="Thời gian ước tính thấp nhất" /></HStack>}
              <Text type="body" hasTabularNumbers>
                {minutesText(c.cost_s)} · {kmText(c.distance_m)}
                {m !== 'input' ? ` · ${improvementText(c.improvement_pct).toLowerCase()}` : ''}
              </Text>
              <Text type="supporting" hasTabularNumbers>
                {seconds(c.cost_s)} · {num(c.distance_m, 0)} m · Thứ tự: {c.stop_order.map(name).join(' → ')}
              </Text>
              <HStack hAlign="end">
                <Button label={isSelected ? 'Đang hiển thị' : 'Xem trên bản đồ'} size="sm"
                  variant={isSelected ? 'primary' : 'secondary'} onClick={() => onSelect(m)} />
              </HStack>
            </VStack>
          </Card>
        )
      })}
      {res.optimal && (
        <Text type="supporting">
          Tham chiếu tối ưu (Held–Karp): {seconds(res.optimal.cost_s)};{' '}
          {res.optimal.gap_pct < 0.05
            ? 'phương án được chọn là tối ưu'
            : `phương án được chọn chậm hơn tối ưu ${num(res.optimal.gap_pct)}%`}
        </Text>
      )}
      <Text type="supporting">
        Thời gian tính toán: ma trận {num(res.matrix_runtime_ms, 2)} ms, sắp thứ tự {num(res.order_runtime_ms ?? 0, 2)} ms
      </Text>
      <Text type="supporting">Điều kiện giao thông: {scenarioLabel}</Text>
    </VStack>
  )
}
