import 'leaflet/dist/leaflet.css'
// Be Vietnam Pro đóng gói trong app (theme SaiGo), máy chiếu không có mạng vẫn đúng chữ và đúng bố cục.
import '@fontsource/be-vietnam-pro/400.css'
import '@fontsource/be-vietnam-pro/500.css'
import '@fontsource/be-vietnam-pro/600.css'
import '@fontsource/be-vietnam-pro/700.css'
import './globals.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { InternationalizationProvider } from '@astryxdesign/core/i18n'
import viVN from '@astryxdesign/core/locales/vi-VN.generated.js'
import { Theme } from '@astryxdesign/core/theme'
import { themes, defaultThemeSlug } from './astryx-themes'
import App from './App'

// Chữ có sẵn của Astryx (liên kết "Bỏ qua đến nội dung", tên bảng…) theo tiếng Việt như trang (test lại 15/11, A-9).
createRoot(document.getElementById('app')!).render(
  <StrictMode>
    <InternationalizationProvider locale="vi-VN" messages={{ 'vi-VN': viVN }}>
      <Theme theme={themes[defaultThemeSlug]}>
        <App />
      </Theme>
    </InternationalizationProvider>
  </StrictMode>,
)
