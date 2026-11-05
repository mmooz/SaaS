import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'

// 忽略 ResizeObserver 循环通知告警：Chrome 对布局观察器的已知良性提示，不影响页面渲染
window.addEventListener('error', (e) => {
  if (e.message && e.message.includes('ResizeObserver loop')) {
    e.preventDefault()
    e.stopImmediatePropagation()
  }
})

// 应用入口：注册 Pinia 状态管理、Element Plus 组件库（中文语言包）与路由
const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus, { locale: zhCn })
app.use(router)
app.mount('#app')
