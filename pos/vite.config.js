import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 配置：POS 收银终端前端
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    host: '0.0.0.0',
    // 忽略 Rust 构建产物，避免 cargo 编译时触发 EBUSY 监听错误
    watch: { ignored: ['**/src-tauri/**'] },
  },
})
