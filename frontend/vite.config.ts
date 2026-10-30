import { defineConfig } from 'vite'

// Backend FastAPI chạy local ở cổng 8000; frontend gọi qua /api.
export default defineConfig({
  // PostCSS rỗng để Vite không đọc nhầm postcss.config ở thư mục cha trên máy dev.
  css: { postcss: {} },
  server: {
    // Cho phép đọc data/demo/cases.json (preset tour, T73) nằm ngoài thư mục frontend.
    fs: { allow: ['..'] },
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
