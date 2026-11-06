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
        <el-menu-item v-if="isSuper" index="/tenants">
          <el-icon><OfficeBuilding /></el-icon><span>租户管理</span>
        </el-menu-item>
        <template v-if="!isSuper">
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon><span>首页仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/stores">
            <el-icon><Shop /></el-icon><span>门店管理</span>
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
        </template>
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
          <!-- 门店切换：点击展开可访问门店，切换后刷新页面使数据范围生效 -->
          <el-dropdown v-if="!isSuper" trigger="click" @command="switchStore">
            <div class="store-chip switchable">
              <el-icon><Shop /></el-icon>
              <span>{{ storeLabel }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="store in storeList"
                  :key="store.id"
                  :command="String(store.id)"
                  :disabled="String(store.id) === String(currentStoreId)"
                >
                  {{ store.name }}
                </el-dropdown-item>
                <el-dropdown-item v-if="!storeList.length" disabled>暂无可切换门店</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div v-else class="store-chip">{{ storeLabel }}</div>
          <el-dropdown>
            <div class="user-chip">
              <el-avatar :size="30" class="user-avatar">{{ avatarChar }}</el-avatar>
              <span>{{ userName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="!isSuper">修改密码</el-dropdown-item>
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
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Odometer, Box, FolderOpened, Avatar, PriceTag, SetUp, DataAnalysis,
  Setting, ArrowDown, OfficeBuilding, Shop,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  clearAdminToken, clearStoreInfo, clearUserInfo, fetchStores, getCurrentStore, getStores,
  getUserInfo, setCurrentStore, setStores,
} from '../api'

const route = useRoute()
const router = useRouter()

// 当前登录用户信息（登录时写入本地缓存）
const user = getUserInfo()

// 是否为平台超级管理员
const isSuper = computed(() => user.role === 'super')

// 当前激活的菜单项（按路由路径匹配）
const activeMenu = computed(() => route.path)

// 当前页面标题（取自路由 meta）
const currentTitle = computed(() => route.meta.title || '鲜衡云')

// 顶部显示的用户名
const userName = computed(() => user.name || user.username || '未登录')

// 顶部头像文字：超级管理员显示「超」，管理员显示「管」，店长显示「店」
const avatarChar = computed(() => {
  if (user.role === 'super') return '超'
  if (user.role === 'admin') return '管'
  return '店'
})

// 可切换的门店列表（登录时写入本地缓存，只保留启用门店）
const storeList = ref(getStores().filter((s) => s.enabled !== false))

// 当前选中的门店 ID
const currentStoreId = ref(getCurrentStore())

// 顶部门店标签：超级管理员显示平台名称，其他角色显示当前门店名
const storeLabel = computed(() => {
  if (isSuper.value) return '平台运营中心'
  const matched = storeList.value.find((s) => String(s.id) === String(currentStoreId.value))
  return matched ? matched.name : '未选择门店'
})

// 同步状态（页面设计阶段使用静态模拟值）
const syncOk = ref(true)

/**
 * 切换当前门店：写入本地缓存并刷新页面，使各页面按新门店重新取数
 * @param {string} storeId 目标门店 ID
 * @returns {void}
 */
const switchStore = (storeId) => {
  if (String(storeId) === String(currentStoreId.value)) return
  const target = storeList.value.find((s) => String(s.id) === String(storeId))
  setCurrentStore(storeId)
  ElMessage.success(`已切换到「${target ? target.name : '新门店'}」`)
  // 整页刷新，确保列表、图表等已加载数据全部切换到新门店范围
  window.location.reload()
}

// 退出登录：清除登录态并跳转登录页
const logout = () => {
  clearAdminToken()
  clearStoreInfo()
  clearUserInfo()
  router.push('/login')
}

/**
 * 拉取最新门店列表，保证门店管理页新增/停用后顶部切换器同步更新
 * @returns {Promise<void>}
 */
const refreshStoreList = async () => {
  if (isSuper.value) return
  try {
    const rows = await fetchStores()
    setStores(rows)
    storeList.value = rows.filter((s) => s.enabled !== false)
    // 当前门店被删除或停用时，自动切到第一个启用门店
    const currentValid = storeList.value.some(
      (s) => String(s.id) === String(currentStoreId.value),
    )
    if (!currentValid) {
      const first = storeList.value[0]
      if (first) {
        setCurrentStore(first.id)
        currentStoreId.value = String(first.id)
      }
    }
  } catch {
    // 拉取失败时沿用登录时缓存的门店列表，不阻断页面使用
  }
}

onMounted(refreshStoreList)
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
.store-chip.switchable {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.store-chip.switchable:hover {
  border-color: var(--brand);
  color: var(--brand);
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
