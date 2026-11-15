// Logo SaiGo (đợt UI "Bàn điều phối", họp thiết kế 9 vai): chữ "S" vẽ thành một tuyến ba đoạn vuông góc nối hai node,
// đầu là vòng rỗng (điểm đi), cuối là chấm teal sáng (điểm đến). Cùng hình với public/favicon.svg.
// Chỉ là hình trang trí đi kèm chữ "SaiGo", nên ẩn với trình đọc màn hình.
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true" focusable="false" style={{ flex: 'none' }}>
      <rect width="28" height="28" rx="8" fill="#1B3532" />
      <path d="M19 8H9.5V14H18.5V20H9" fill="none" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="19" cy="8" r="2.5" fill="#1B3532" stroke="#FFFFFF" strokeWidth="1.8" />
      <circle cx="9" cy="20" r="2.7" fill="#4FD1C1" />
    </svg>
  )
}
