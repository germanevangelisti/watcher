import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // Corregido de 8001 a 8000
        changeOrigin: true,
        secure: false,
        timeout: 600000,  // 10 minutos para procesamiento largo
        proxyTimeout: 600000,
        ws: true,  // Soporte para WebSockets
      }
    }
  }
})
