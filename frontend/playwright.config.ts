// Kiểm tra giao diện đầu-cuối theo kịch bản DEMO (docs/DEMO.md mục 2) ở khung máy chiếu 1280 × 800.
// Cần đồ thị thật data/processed/hcm-benthanh-r2000-20261024.json (không nằm trong repo, dựng bằng
// scripts/setup_dev), nên chỉ chạy ở máy local: `npm run e2e`. Server đang chạy sẵn thì dùng lại, nên khi có
// Vite của nhánh khác đang chiếm 5173 thì đặt E2E_PORT (vd. `$env:E2E_PORT = 5174`) để test đúng code của nhánh này.
import { defineConfig, devices } from '@playwright/test'

const port = process.env.E2E_PORT ?? '5173'
const python = process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python'

export default defineConfig({
  testDir: 'e2e',
  outputDir: 'e2e-results',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${port}`,
    viewport: { width: 1280, height: 800 },
    locale: 'vi-VN',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } } }],
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --app-dir backend --port 8000`,
      cwd: '..',
      env: { SAIGO_GRAPH: 'data/processed/hcm-benthanh-r2000-20261024.json' },
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: `npm run dev -- --port ${port} --strictPort`,
      url: `http://localhost:${port}`,
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
