// Ô số chính của cột kết quả (đợt UI 15/11, họp thiết kế 5 vai): số lớn đọc được từ xa trên máy chiếu, đơn vị nhỏ cạnh
// số, nhãn ở trên, số gốc (giây, mét) ở dòng phụ. Chỉ hiển thị lại số đã có trong response, không tính số mới.
import { Card } from '@astryxdesign/core/Card'
import { HStack } from '@astryxdesign/core/HStack'
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'

const vn = (x: number, d: number) => x.toLocaleString('vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d })

/** Giây → ["4,1", "phút"]. */
export const minutes = (s: number): [string, string] => [vn(s / 60, 1), 'phút']
/** Mét → ["1,6", "km"] (từ 1 km) hoặc ["850", "m"]. */
export const km = (m: number): [string, string] => (m >= 1000 ? [vn(m / 1000, 1), 'km'] : [vn(m, 0), 'm'])
/** Dạng một chuỗi cho dòng văn bản: "4,1 phút", "1,6 km". */
export const minutesText = (s: number) => minutes(s).join(' ')
export const kmText = (m: number) => km(m).join(' ')
/** Giây và mét gốc cho dòng phụ: "246,1 s", "1.748 m". */
export const secondsRaw = (s: number) => `${vn(s, 1)} s`
export const metersRaw = (m: number) => `${vn(m, 0)} m`

export default function Kpi({ label, value, sub }: { label: string; value: [string, string] | string; sub?: string }) {
  const [num, unit] = typeof value === 'string' ? [value, ''] : value
  return (
    <Card variant="muted" padding={3}>
      <VStack gap={0.5}>
        <Text type="supporting">{label}</Text>
        <HStack gap={1} vAlign="end">
          <Text type="display-3" hasTabularNumbers textWrap="nowrap">{num}</Text>
          {unit && <Text type="body" weight="semibold">{unit}</Text>}
        </HStack>
        {sub && <Text type="supporting" hasTabularNumbers>{sub}</Text>}
      </VStack>
    </Card>
  )
}
