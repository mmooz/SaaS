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

/**
 * 读取本地保存的登录收银员信息（与 posStore 使用同一键名）
 * @returns {object|null} 收银员信息，未登录时为 null
 */
function loadCashier() {
  try {
    return JSON.parse(localStorage.getItem('pos_cashier') || 'null')
  } catch {
    return null
  }
}

// 路由守卫：设置页面标题；未登录时拦截到登录页
router.beforeEach((to) => {
  document.title = `${to.meta.title || '收银台'} · 鲜衡 POS`
  const cashier = loadCashier()
  // 未登录只允许停留在登录页，登录后回到原目标页
  if (!cashier && to.name !== 'Login') {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  // 已登录时不再展示登录页（需切换收银员请先退出登录）
  if (cashier && to.name === 'Login') {
    return { name: 'PosMain' }
  }
  return true
})

export default router
