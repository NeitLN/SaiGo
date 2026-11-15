// Nhóm chip một lựa chọn và danh sách bấm một lần (đợt UI "Bàn điều phối", họp thiết kế 9 vai).
// Astryx chưa có nhóm chip xuống dòng được (SegmentedControl không xuống dòng, nhãn dài bị cắt ở panel 360 px), nên
// viết theo mẫu radiogroup của WAI-ARIA: một chip nhận Tab, phím mũi tên chuyển và chọn luôn.
import { useRef, type KeyboardEvent } from 'react'
import { Text } from '@astryxdesign/core/Text'
import { VStack } from '@astryxdesign/core/VStack'

export interface ChipOption {
  value: string
  label: string
  title?: string   // câu đầy đủ khi rê chuột (nhãn chip là bản rút gọn)
}

const Check = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor"
    strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5 9-10" /></svg>
)

export function ChipRadioGroup({ id, label, options, value, onChange }: {
  id: string
  label: string
  options: ChipOption[]
  value: string
  onChange: (v: string) => void
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])
  const current = options.findIndex((o) => o.value === value)
  const move = (from: number, step: number) => {
    const n = (from + step + options.length) % options.length
    onChange(options[n].value)
    refs.current[n]?.focus()
  }
  const onKey = (i: number) => (e: KeyboardEvent) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); move(i, 1) }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); move(i, -1) }
  }
  return (
    <VStack gap={2}>
      <Text type="label" id={`${id}-label`}>{label}</Text>
      <div role="radiogroup" aria-labelledby={`${id}-label`} className="chips">
        {options.map((o, i) => {
          const on = o.value === value
          return (
            <button key={o.value} ref={(el) => { refs.current[i] = el }} type="button" role="radio" aria-checked={on}
              tabIndex={on || (current < 0 && i === 0) ? 0 : -1} title={o.title} className={on ? 'chip is-on' : 'chip'}
              onClick={() => onChange(o.value)} onKeyDown={onKey(i)}>
              {on && <Check />}{o.label}
            </button>
          )
        })}
      </div>
    </VStack>
  )
}

/** Danh sách bấm một lần (lộ trình mẫu): mỗi dòng là một nút; dòng đang mở có dấu chọn và aria-pressed. */
export function PickList({ id, label, options, value, onPick, isDisabled, disabledMessage }: {
  id: string
  label: string
  options: ChipOption[]
  value: string
  onPick: (v: string) => void
  isDisabled?: boolean
  disabledMessage?: string
}) {
  return (
    <VStack gap={2}>
      <Text type="label" id={`${id}-label`}>{label}</Text>
      <div role="group" aria-labelledby={`${id}-label`} className="pick-list">
        {options.map((o) => {
          const on = o.value === value
          return (
            <button key={o.value} type="button" aria-pressed={on} aria-disabled={isDisabled || undefined} title={o.title}
              className={on ? 'pick is-on' : 'pick'} onClick={() => { if (!isDisabled) onPick(o.value) }}>
              <span className="pick-check">{on && <Check />}</span>{o.label}
            </button>
          )
        })}
      </div>
      {isDisabled && disabledMessage && <Text type="supporting">{disabledMessage}</Text>}
    </VStack>
  )
}

/**
 * Danh sách đoạn để đóng (đánh giá dùng thử 16/11): thay ô chọn của Astryx, vì ô chọn không báo mục đang rê nên
 * không xem trước được. Rê chuột / Tab tới một dòng thì `onPreview(i)` (bản đồ tô đỏ đoạn đó); bấm hay Enter là đóng,
 * vẫn một bước như trước. Danh sách cuộn trong khung thấp để không đẩy panel dài ra.
 */
export function SegmentList({ id, label, items, onPick, onPreview }: {
  id: string
  label: string
  items: string[]
  onPick: (i: number) => void
  onPreview: (i: number | null) => void
}) {
  return (
    <VStack gap={2}>
      <Text type="label" id={`${id}-label`}>{label}</Text>
      <div role="group" aria-labelledby={`${id}-label`} className="segment-list" onMouseLeave={() => onPreview(null)}>
        {items.map((text, i) => (
          <button key={text} type="button" className="pick segment-pick"
            onMouseEnter={() => onPreview(i)} onFocus={() => onPreview(i)} onBlur={() => onPreview(null)}
            onClick={() => { onPreview(null); onPick(i) }}>
            {text}
          </button>
        ))}
      </div>
    </VStack>
  )
}
