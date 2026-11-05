<template>
  <el-container class="admin-layout">
    <!-- 侧边导航栏 -->
    <el-aside width="216px" class="admin-aside">
      <div class="brand">
        <div class="brand-logo">衡</div>
        <div>
          <div class="brand-name">鲜衡云</div>
          <div class="brand-sub">电子秤收银系统</div>
        </div>
      </div>
      <el-menu :default-active="activeMenu" router class="side-menu">
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon><span>首页仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/products">
          <el-icon><Box /></el-icon><span>商品管理</span>
        </el-menu-item>
        <el-menu-item index="/categories">
          <el-icon><FolderOpened /></el-icon><span>分类管理</span>
        </el-menu-item>
        <el-menu-item index="/members">
          <el-icon><Avatar /></el-icon><span>会员管理</span>
        </el-menu-item>
        <el-menu-item index="/promotions">
          <el-icon><PriceTag /></el-icon><span>促销管理</span>
        </el-menu-item>
        <el-menu-item index="/inventory">
          <el-icon><SetUp /></el-icon><span>库存管理</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><DataAnalysis /></el-icon><span>报表中心</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon><span>系统设置</span>
        </el-menu-item>
      </el-menu>
      <div class="aside-footer">
        <div class="sync-badge" :class="{ ok: syncOk }">
          <span class="dot" :class="{ ok: syncOk }"></span>
          {{ syncOk ? '数据已同步' : '同步中…' }}
        </div>
      </div>
    </el-aside>

    <el-container class="admin-main">
      <!-- 顶部栏 -->
      <el-header class="admin-header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">
          <div class="store-chip">鲜果超市 · 总店</div>
          <el-dropdown>
            <div class="user-chip">
              <el-avatar :size="30" class="user-avatar">店</el-avatar>
              <span>店长 王</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>切换门店</el-dropdown-item>
                <el-dropdown-item>修改密码</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="admin-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Odometer, Box, FolderOpened, Avatar, PriceTag, SetUp, DataAnalysis,
  Setting, ArrowDown,
} from '@element-plus/icons-vue'
import { clearAdminToken } from '../api'

const route = useRoute()
const router = useRouter()

// 当前激活的菜单项（按路由路径匹配）
const activeMenu = computed(() => route.path)

// 当前页面标题（取自路由 meta）
const currentTitle = computed(() => route.meta.title || '鲜衡云')

// 同步状态（页面设计阶段使用静态模拟值）
const syncOk = ref(true)

// 退出登录：跳转登录页
const logout = () => {
  router.push('/login')
}
</script>

<style scoped>
.admin-layout {
  height: 100vh;
}
.admin-aside {
  background: var(--neutral-900);
  color: #fff;
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 18px 16px;
}
.brand-logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--brand), oklch(60% 0.15 120));
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px oklch(52% 0.15 152 / 0.4);
}
.brand-name {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 1px;
}
.brand-sub {
  font-size: 11px;
  color: oklch(80% 0.02 152);
}
.side-menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
  padding: 8px;
}
.side-menu :deep(.el-menu-item) {
  color: oklch(85% 0.02 152);
  border-radius: 8px;
  margin-bottom: 4px;
  height: 46px;
}
.side-menu :deep(.el-menu-item:hover) {
  background: oklch(25% 0.015 152);
  color: #fff;
}
.side-menu :deep(.el-menu-item.is-active) {
  background: var(--brand);
  color: #fff;
  font-weight: 600;
}
.aside-footer {
  padding: 14px 18px;
  border-top: 1px solid oklch(30% 0.02 152);
}
.sync-badge {
  font-size: 12px;
  color: oklch(80% 0.02 152);
  display: flex;
  align-items: center;
  gap: 8px;
}
.sync-badge .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: oklch(70% 0.1 60);
}
.sync-badge.ok .dot {
  background: oklch(65% 0.15 155);
  box-shadow: 0 0 0 3px oklch(65% 0.15 155 / 0.18);
}
.admin-header {
  background: #fff;
  border-bottom: 1px solid var(--neutral-200);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
}
.header-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--neutral-900);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.store-chip {
  font-size: 13px;
  color: var(--neutral-600);
  background: var(--neutral-100);
  border: 1px solid var(--neutral-200);
  border-radius: 999px;
  padding: 4px 14px;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--neutral-700);
  font-size: 13px;
}
.user-avatar {
  background: var(--brand);
  color: #fff;
  font-size: 13px;
}
.admin-content {
  background: var(--neutral-50);
  padding: 20px;
  overflow: auto;
}
</style>
