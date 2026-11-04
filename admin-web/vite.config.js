import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 配置：Web 后台管理前端
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: '0.0.0.0',
  },
})
