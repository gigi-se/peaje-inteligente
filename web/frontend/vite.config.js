import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, las llamadas /api y /ws van al Django que corre en el servidor de pruebas.
// Cambia DEV_BACKEND solo para programar; en producción Nginx sirve todo bajo el mismo dominio.
const DEV_BACKEND = process.env.DEV_BACKEND || 'http://localhost:8001'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': DEV_BACKEND, '/media': DEV_BACKEND, '/ws': { target: DEV_BACKEND, ws: true } } },
})
