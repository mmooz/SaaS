import { createRouter, createWebHistory } from 'vue-router'

// 路由表：POS 收银终端各页面
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '收银员登录' },
  },
  {
    path: '/',
    name: 'PosMain',
    component: () => import('../views/PosMain.vue'),
    meta: { title: '收银台' },
  },
  {
    path: '/shift',
    name: 'Shift',
    component: () => import('../views/Shift.vue'),
    meta: { title: '交接班' },
  },
  {
    path: '/refund',
    name: 'Refund',
    component: () => import('../views/Refund.vue'),
    meta: { title: '退款退货' },
  },
  {
    path: '/reprint',
    name: 'Reprint',
    component: () => import('../views/Reprint.vue'),
    meta: { title: '补打' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { title: '系统设置' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：设置页面标题
router.beforeEach((to) => {
  document.title = `${to.meta.title || '收银台'} · 鲜衡 POS`
  return true
})

export default router
