import { createRouter, createWebHistory } from 'vue-router'
import AdminLayout from '../layouts/AdminLayout.vue'
import { getAdminToken, isSuperAdmin } from '../api'

// 路由表：Web 后台管理各页面
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: AdminLayout,
    children: [
      { path: '', redirect: () => (isSuperAdmin() ? '/tenants' : '/dashboard') },
      { path: 'tenants', name: 'Tenants', component: () => import('../views/Tenants.vue'), meta: { title: '租户管理', superOnly: true } },
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '首页仪表盘' } },
      { path: 'stores', name: 'Stores', component: () => import('../views/Stores.vue'), meta: { title: '门店管理' } },
      { path: 'orders', name: 'Orders', component: () => import('../views/Orders.vue'), meta: { title: '订单管理' } },
      { path: 'shifts', name: 'Shifts', component: () => import('../views/Shifts.vue'), meta: { title: '交接班' } },
      { path: 'products', name: 'Products', component: () => import('../views/Products.vue'), meta: { title: '商品管理' } },
      { path: 'categories', name: 'Categories', component: () => import('../views/Categories.vue'), meta: { title: '分类管理' } },
      { path: 'members', name: 'Members', component: () => import('../views/Members.vue'), meta: { title: '会员管理' } },
      { path: 'promotions', name: 'Promotions', component: () => import('../views/Promotions.vue'), meta: { title: '促销管理' } },
      { path: 'inventory', name: 'Inventory', component: () => import('../views/Inventory.vue'), meta: { title: '库存管理' } },
      { path: 'reports', name: 'Reports', component: () => import('../views/Reports.vue'), meta: { title: '报表中心' } },
      { path: 'settings', name: 'Settings', component: () => import('../views/Settings.vue'), meta: { title: '系统设置' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录跳转登录页，已登录访问登录页则回首页；超级管理员专属页面做权限校验
router.beforeEach((to) => {
  document.title = `${to.meta.title || ''} · 鲜衡云`
  // 无令牌时除登录页外一律跳登录
  if (to.path !== '/login' && !getAdminToken()) return '/login'
  // 已有令牌时访问登录页：超级管理员去租户管理，其他角色回仪表盘
  if (to.path === '/login' && getAdminToken()) return isSuperAdmin() ? '/tenants' : '/dashboard'
  // 超级管理员专属页面：非超级管理员重定向到仪表盘
  if (to.meta.superOnly && !isSuperAdmin()) return '/dashboard'
  return true
})

export default router
