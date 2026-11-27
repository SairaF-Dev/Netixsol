import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API runs on :8010 (8000 is often taken by other local containers) (uvicorn ilm.api.main:app). In dev, /api is proxied so the session
// cookie stays same-origin; in production the app and API share a domain the same way.
// The code editor is split into its own file by the lazy route in App.tsx.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': process.env.ILM_API ?? 'http://localhost:8010' } },
})
