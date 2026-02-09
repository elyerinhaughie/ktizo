import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Proxy is disabled for native installation
    // The frontend uses absolute URLs with dynamic hostname detection
    // If you need proxy for Docker, uncomment and set target to your backend URL
    // proxy: {
    //   '/api': {
    //     target: 'http://backend:8000',
    //     changeOrigin: true
    //   }
    // }
  }
})
