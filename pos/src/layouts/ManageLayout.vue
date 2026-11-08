<template>
  <el-container class="manage-layout">
    <!-- 侧边导航栏 -->
    <el-aside width="208px" class="manage-aside">
      <div class="brand">
        <div class="brand-logo">衡</div>
        <div>
          <div class="brand-name">鲜衡云</div>
          <div class="brand-sub">电子秤收银系统</div>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="openGroups"
        router
        class="side-menu"
      >
        <el-menu-item v-if="isManager" index="/manage">
          <el-icon><Odometer /></el-icon><span>首页仪表盘</span>
        </el-menu-item>
        <el-sub-menu v-if="isManager" index="g-data">
          <template #title><el-icon><Box /></el-icon><span>基础数据</span></template>
          <el-menu-item index="/manage/products"><el-icon><Box /></el-icon>商品管理</el-menu-item>
          <el-menu-item index="/manage/categories"><el-icon><FolderOpened /></el-icon>分类管理</el-menu-item>
          <el-menu-item index="/manage/members"><el-icon><Avatar /></el-icon>会员管理</el-menu-item>
          <el-menu-item index="/manage/promotions"><el-icon><PriceTag /></el-icon>促销管理</el-menu-item>
          <el-menu-item index="/manage/inventory"><el-icon><SetUp /></el-icon>库存管理</el-menu-item>
        </el-sub-menu>
        <el-menu-item v-if="isManager" index="/manage/reports">
          <el-icon><DataAnalysis /></el-icon><span>报表中心</span>
        </el-menu-item>
        <el-sub-menu index="g-biz">
          <template #title><el-icon><Tickets /></el-icon><span>业务办理</span></template>
          <el-menu-item index="/orders"><el-icon><Tickets /></el-icon>订单查询</el-menu-item>
          <el-menu-item index="/shift"><el-icon><Clock /></el-icon>交接班</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="g-sys">
          <template #title><el-icon><Setting /></el-icon><span>系统</span></template>
          <el-menu-item index="/settings"><el-icon><Setting /></el-icon>系统设置</el-menu-item>
          <el-menu-item index="/"><el-icon><ArrowLeft /></el-icon>返回收银台</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container class="manage-main">
      <!-- 顶部栏 -->
      <el-header class="manage-header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">
          <div class="store-chip">
            <el-icon><Shop /></el-icon>
            <span>{{ storeLabel }}</span>
          </div>
          <el-dropdown>
            <div class="user-chip">
              <el-avatar :size="30" class="user-avatar">{{ avatarChar }}</el-avatar>
              <span>{{ userName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="manage-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Odometer, Box, FolderOpened, Avatar, PriceTag, SetUp, DataAnalysis,
  Setting, ArrowDown, ArrowLeft, Shop, Tickets, Clock,
} from '@element-plus/icons-vue'
import { clearAuthToken, clearStoreInfo, getCurrentStore, getStores } from '../api'

const route = useRoute()
const router = useRouter()

// 当前登录收银员信息（与 posStore 共用同一本地键 pos_cashier）
function loadCashier() {
  try {
    return JSON.parse(localStorage.getItem('pos_cashier') || 'null')
  } catch {
    return null
  }
}
const cashier = loadCashier() || {}

// 店长及以上角色：控制敏感数据页菜单显隐，普通店员仅见订单查询/交接班/设置等
const isManager = computed(() => ['admin', 'manager', 'super'].includes(cashier.role))

// 当前激活的菜单项（按路由路径匹配）
const activeMenu = computed(() => route.path)

// 当前路由所属分组：加载时自动展开对应子菜单，避免进入子页后菜单折叠
const openGroups = computed(() => {
  const p = route.path
  if (['/manage/products', '/manage/categories', '/manage/members', '/manage/promotions', '/manage/inventory'].includes(p)) {
    return ['g-data']
  }
  if (['/orders', '/shift'].includes(p)) {
    return ['g-biz']
  }
  if (['/settings', '/'].includes(p)) {
    return ['g-sys']
  }
  return []
})

// 当前页面标题（取自路由 meta）
const currentTitle = computed(() => route.meta.title || '管理后台')

// 顶部显示的用户名
const userName = computed(() => cashier.name || cashier.no || '未登录')
const avatarChar = computed(() => (userName.value || '?').slice(0, 1))

// 当前门店名称（POS 始终操作当前门店，无切换器）
const storeLabel = computed(() => {
  const id = String(getCurrentStore())
  const list = getStores()
  const found = list.find((s) => String(s.id) === id)
  return found ? found.name : id || '未选择门店'
})

const logout = () => {
  clearAuthToken()
  clearStoreInfo()
  localStorage.removeItem('pos_cashier')
  router.replace('/login')
}
</script>

<style scoped>
.manage-layout {
  height: 100vh;
}
.manage-aside {
  background: #fff;
  border-right: 1px solid var(--el-border-color-light);
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px;
  border-bottom: 1px solid var(--el-border-color-light);
}
.brand-logo {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, #1677ff, #36cfc9);
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-name {
  font-size: 16px;
  font-weight: 700;
}
.brand-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.side-menu {
  border-right: none;
  flex: 1;
  padding-top: 8px;
}
.manage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
}
.header-title {
  font-size: 17px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.store-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  padding: 6px 10px;
  border-radius: 8px;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 14px;
}
.user-avatar {
  background: #1677ff;
  color: #fff;
}
.manage-content {
  background: #f5f7fa;
  padding: 16px;
}
</style>
