// Theme riêng của SaiGo (đợt UI "Bàn điều phối", họp thiết kế 9 vai, Tiến duyệt 16/11). Kế thừa theme neutral,
// chỉ đổi màu và font:
// - teal chỉ dành cho thao tác (nút chính, mục đang chọn); màu dữ liệu trên bản đồ giữ ở layers.ts;
// - nền trung tính hơi ngả xanh thay xám thuần;
// - chữ Be Vietnam Pro, đóng gói trong app (main.tsx nạp @fontsource), không tải từ mạng lúc chạy.
// Sửa xong chạy `npx astryx theme build src/themes/saigo/saigoTheme.ts` để dựng lại file built.
import { defineTheme } from '@astryxdesign/core/theme'
import { neutralTheme } from '@astryxdesign/theme-neutral'

const fallbacks = "'Segoe UI', system-ui, -apple-system, Roboto, Arial, sans-serif"

export const saigoTheme = defineTheme({
  name: 'saigo',
  extends: neutralTheme,
  // Cấu hình chữ của theme con thay hẳn cấu hình gốc, nên ghi lại thang 14 / 1,2 của neutral; khai báo ở đây (không
  // chỉ đổi token --font-family-*) để quy tắc màn hình cảm ứng hẹp của neutral cũng dựng lại bằng Be Vietnam Pro.
  typography: {
    scale: { base: 14, ratio: 1.2 },
    body: { family: 'Be Vietnam Pro', fallbacks },
    heading: { family: 'Be Vietnam Pro', fallbacks, weights: { 3: 'bold', 4: 'bold' } },
  },
  tokens: {
    '--color-accent': ['#0B6B63', '#4FD1C1'],
    '--color-accent-muted': ['#E6F2F0', '#12332F'],
    '--color-on-accent': ['#FFFFFF', '#04201D'],
    '--color-text-accent': ['#0B6B63', '#4FD1C1'],
    '--color-icon-accent': ['#0B6B63', '#4FD1C1'],

    '--color-background-body': ['#F3F5F4', '#0E1413'],
    '--color-background-surface': ['#FFFFFF', '#161D1C'],
    '--color-background-card': ['#FFFFFF', '#161D1C'],
    '--color-background-popover': ['#FFFFFF', '#1D2625'],
    '--color-background-muted': ['#EEF2F1', '#1D2625'],

    '--color-text-primary': ['#16201F', '#E8EEEC'],
    '--color-text-secondary': ['#4E5C5A', '#A7B4B1'],
    '--color-icon-primary': ['#16201F', '#E8EEEC'],
    '--color-icon-secondary': ['#5D6B69', '#8E9B98'],
    '--color-border': ['#DCE3E1', '#2A3533'],
    '--color-border-emphasized': ['#8A9693', '#4A5754'],

    // Chênh lệch "chậm hơn" dùng chữ hổ phách (≥ 4,5:1 cả hai chế độ), đỏ chỉ cho lỗi.
    '--color-success': ['#1B7F3B', '#5FB97E'],
    '--color-text-success': ['#1B7F3B', '#5FB97E'],
    '--color-text-warning': ['#B45309', '#FBBF24'],
    '--color-error': ['#B42318', '#F07A72'],
    '--color-text-error': ['#B42318', '#F07A72'],
  },
})
