import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend FastAPI chạy local ở cổng 8000; frontend gọi qua /api.
export default defineConfig({
  plugins: [react()],
  // PostCSS rỗng để Vite không đọc nhầm postcss.config ở thư mục cha trên máy dev.
  css: { postcss: {} },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
    // Cho phép đọc data/demo/cases.json (T55) ở ngoài thư mục frontend.
    fs: { allow: ['..'] },
  },
})
