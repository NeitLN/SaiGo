import 'leaflet/dist/leaflet.css'
import './globals.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Theme } from '@astryxdesign/core/theme'
import { themes, defaultThemeSlug } from './astryx-themes'
import App from './App'

createRoot(document.getElementById('app')!).render(
  <StrictMode>
    <Theme theme={themes[defaultThemeSlug]}>
      <App />
    </Theme>
  </StrictMode>,
)
