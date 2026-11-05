<template>
  <div class="settings">
    <div class="settings-body card">
      <!-- 左侧设置导航 -->
      <el-menu :default-active="activeMenu" class="settings-menu" @select="(idx) => (activeMenu = idx)">
        <el-menu-item index="store"><el-icon><Shop /></el-icon><span>门店信息</span></el-menu-item>
        <el-menu-item index="cashier"><el-icon><Operation /></el-icon><span>收银参数</span></el-menu-item>
        <el-menu-item index="users"><el-icon><User /></el-icon><span>用户权限</span></el-menu-item>
        <el-menu-item index="logs"><el-icon><Document /></el-icon><span>操作日志</span></el-menu-item>
        <el-menu-item index="backup"><el-icon><FolderChecked /></el-icon><span>数据备份</span></el-menu-item>
      </el-menu>

      <!-- 右侧内容区 -->
      <div class="settings-content">
        <!-- ========== 门店信息 ========== -->
        <div v-show="activeMenu === 'store'">
          <h3 class="section-title">门店信息</h3>
          <el-form :model="storeForm" label-width="110px" class="setting-form">
            <el-form-item label="门店名称">
              <el-input v-model="storeForm.name" style="max-width: 380px" />
            </el-form-item>
            <el-form-item label="联系电话">
              <el-input v-model="storeForm.phone" style="max-width: 380px" />
            </el-form-item>
            <el-form-item label="门店地址">
              <el-input v-model="storeForm.address" style="max-width: 480px" />
            </el-form-item>
            <el-form-item label="小票抬头">
              <el-input v-model="storeForm.receiptTitle" placeholder="打印在小票顶部的门店名称" style="max-width: 480px" />
            </el-form-item>
            <el-form-item label="小票底部广告语">
              <el-input v-model="storeForm.receiptAd" type="textarea" :rows="2" placeholder="如：新鲜每一天，健康千万家" style="max-width: 480px" />
            </el-form-item>
            <el-form-item label="标签纸规格">
              <el-select v-model="storeForm.labelSpec" style="width: 200px">
                <el-option label="58mm 热敏标签" value="58mm" />
                <el-option label="60mm 热敏标签" value="60mm" />
              </el-select>
            </el-form-item>
            <el-form-item label="小票规格">
              <el-select v-model="storeForm.receiptSpec" style="width: 200px">
                <el-option label="58mm 小票" value="58" />
                <el-option label="80mm 小票" value="80" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveGroup('store', storeForm, '门店信息已保存')">保存设置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- ========== 收银参数 ========== -->
        <div v-show="activeMenu === 'cashier'">
          <h3 class="section-title">收银参数</h3>
          <el-form label-width="180px" class="setting-form">
            <el-form-item label="称重稳定自动确认">
              <el-switch v-model="cashierForm.autoConfirm" inline-prompt active-text="自动" inactive-text="手动" />
              <span class="form-hint">称重数值稳定后自动打印标签</span>
            </el-form-item>
            <el-form-item label="积分比例">
              <span class="form-hint">消费 1 元 = </span>
              <el-input-number v-model="cashierForm.pointRatio" :min="0.1" :step="0.1" style="width: 120px" />
              <span class="form-hint">分（默认 1 元 = 1 分）</span>
            </el-form-item>
            <el-form-item label="积分抵扣">
              <span class="form-hint">100 分 = </span>
              <el-input-number v-model="cashierForm.pointDeduct" :min="0.1" :step="0.1" style="width: 120px" />
              <span class="form-hint">元</span>
            </el-form-item>
            <el-form-item label="储值充值赠送比例">
              <el-input-number v-model="cashierForm.rechargeGift" :min="0" :step="1" style="width: 120px" />
              <span class="form-hint">%（充 100 送 10 即填 10）</span>
            </el-form-item>
            <el-form-item label="允许负库存">
              <el-switch v-model="cashierForm.allowNegative" inline-prompt active-text="允许" inactive-text="禁止" />
              <span class="form-hint">开启后库存不足仍可销售</span>
            </el-form-item>
            <el-form-item label="数据同步间隔">
              <el-select v-model="cashierForm.syncInterval" style="width: 200px">
                <el-option label="实时同步" value="0" />
                <el-option label="5 分钟" value="5" />
                <el-option label="15 分钟" value="15" />
                <el-option label="30 分钟" value="30" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveGroup('cashier', cashierForm, '收银参数已保存')">保存设置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- ========== 用户权限 ========== -->
        <div v-show="activeMenu === 'users'">
          <div class="content-head">
            <h3 class="section-title">用户权限</h3>
            <el-button type="primary" :icon="Plus" @click="openAddUser">新增用户</el-button>
          </div>
          <el-table :data="users" empty-text="暂无用户" class="content-table">
            <el-table-column prop="username" label="用户名" width="130" />
            <el-table-column prop="name" label="姓名" width="120" />
            <el-table-column label="角色" width="110" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="roleTag(row.role)" effect="light">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === '启用' ? 'success' : 'info'" effect="light">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="130" align="center">
              <template #default="{ row }"><span class="cell-time">{{ row.createdAt }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="170" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editUser(row)">编辑</el-button>
                <el-button link type="warning" size="small" @click="resetPassword(row)">重置密码</el-button>
              </template>
            </el-table-column>
          </el-table>
          <!-- 权限说明卡片 -->
          <div class="perm-card">
            <div class="perm-title">角色权限说明</div>
            <div class="perm-grid">
              <div class="perm-item">
                <el-tag size="small" type="danger" effect="light">管理员</el-tag>
                <span>全部权限：门店设置、收银参数、用户管理、数据备份</span>
              </div>
              <div class="perm-item">
                <el-tag size="small" type="warning" effect="light">店长</el-tag>
                <span>经营管理：促销、库存、报表，可查看操作日志</span>
              </div>
              <div class="perm-item">
                <el-tag size="small" type="info" effect="light">收银员</el-tag>
                <span>收银收银：开单、结账、称重，仅可查看本店数据</span>
              </div>
            </div>
          </div>
          <!-- 新增 / 编辑用户弹窗 -->
          <el-dialog v-model="userDialog" :title="userForm.id ? '编辑用户' : '新增用户'" width="440px" destroy-on-close>
            <el-form label-width="80px">
              <el-form-item label="用户名" required>
                <el-input v-model="userForm.username" placeholder="登录账号" :disabled="!!userForm.id" />
              </el-form-item>
              <el-form-item label="姓名" required>
                <el-input v-model="userForm.name" placeholder="真实姓名" />
              </el-form-item>
              <el-form-item label="角色" required>
                <el-select v-model="userForm.role" style="width: 100%">
                  <el-option label="管理员" value="admin" />
                  <el-option label="店长" value="manager" />
                  <el-option label="收银员" value="cashier" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="!userForm.id" label="初始密码">
                <el-input v-model="userForm.password" placeholder="默认 123456" />
              </el-form-item>
              <el-form-item v-else label="账号状态">
                <el-switch v-model="userForm.enabled" active-text="启用" inactive-text="停用" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="userDialog = false">取消</el-button>
              <el-button type="primary" :loading="userSaving" @click="saveUser">保存</el-button>
            </template>
          </el-dialog>
        </div>

        <!-- ========== 操作日志 ========== -->
        <div v-show="activeMenu === 'logs'">
          <div class="content-head">
            <h3 class="section-title">操作日志</h3>
            <el-input
              v-model="logKeyword"
              placeholder="搜索操作人 / 内容"
              clearable
              :prefix-icon="Search"
              style="width: 240px"
              @keyup.enter="searchLogs"
              @clear="searchLogs"
            />
          </div>
          <el-table :data="logs" empty-text="暂无日志记录" class="content-table">
            <el-table-column label="时间" width="150" align="right">
              <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
            </el-table-column>
            <el-table-column prop="operator" label="操作人" width="100" align="center" />
            <el-table-column prop="role" label="角色" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="roleTag(row.role)" effect="light">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="actionText" label="操作内容" min-width="220" show-overflow-tooltip />
          </el-table>
          <el-pagination
            class="pager"
            background
            layout="total, prev, pager, next"
            :total="logTotal"
            :page-size="logPageSize"
            :current-page="logPage"
            @current-change="loadLogs"
          />
        </div>

        <!-- ========== 数据备份 ========== -->
        <div v-show="activeMenu === 'backup'">
          <h3 class="section-title">数据备份</h3>
          <div class="backup-tip card-inner">
            <div>
              <div class="tip-title"><el-icon><InfoFilled /></el-icon> 备份说明</div>
              <p class="tip-desc">系统每日 02:00 自动备份一次全部经营数据（商品、库存、订单、会员）。建议在重大调整前手动备份，备份文件保留最近 30 天。</p>
            </div>
            <el-button type="primary" :icon="Refresh" @click="backupNow">立即备份</el-button>
          </div>
          <el-table :data="backupHistory" empty-text="暂无备份记录" class="content-table">
            <el-table-column label="备份时间" width="150" align="right">
              <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
            </el-table-column>
            <el-table-column prop="name" label="文件名" min-width="170" show-overflow-tooltip />
            <el-table-column prop="size" label="大小" width="100" align="right">
              <template #default="{ row }"><span class="num">{{ row.size }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="90" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Shop, Operation, User, Document, FolderChecked, InfoFilled } from '@element-plus/icons-vue'
import {
  fetchSettings,
  saveSettings,
  fetchUsers,
  createUser,
  updateUser,
  resetUserPassword,
  fetchOperationLogs,
  fetchBackups,
  createBackup,
  backupDownloadUrl,
} from '../api'

// 当前设置子菜单
const activeMenu = ref('store')

// 角色代码 -> 中文名称
const ROLE_NAMES = { admin: '管理员', manager: '店长', cashier: '收银员' }

/**
 * 角色标签颜色：管理员红 / 店长橙 / 收银员蓝
 * @param {string} role 角色代码或中文名称
 * @returns {string} el-tag 类型
 */
const roleTag = (role) =>
  role === 'admin' || role === '管理员'
    ? 'danger'
    : role === 'manager' || role === '店长'
      ? 'warning'
      : 'info'

/**
 * 格式化 ISO 时间字符串为 yyyy-MM-dd HH:mm:ss
 * @param {string} iso 服务端时间
 * @returns {string} 格式化时间
 */
const formatTime = (iso) => (iso || '').replace('T', ' ').slice(0, 19)

/**
 * 把字节数格式化为 KB/MB
 * @param {number} bytes 字节数
 * @returns {string} 可读大小
 */
const formatSize = (bytes) => {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(1)} KB`
}

// ---------- 门店信息表单 ----------
const storeForm = reactive({
  name: '鲜果超市 · 总店',
  phone: '0512-88886666',
  address: '苏州市姑苏区平江路 88 号',
  receiptTitle: '鲜果超市（总店）',
  receiptAd: '新鲜每一天，健康千万家',
  labelSpec: '58mm',
  receiptSpec: '58',
})

// ---------- 收银参数表单 ----------
const cashierForm = reactive({
  autoConfirm: true,
  pointRatio: 1,
  pointDeduct: 0.1,
  rechargeGift: 10,
  allowNegative: false,
  syncInterval: '5',
})

// 加载服务端门店信息与收银参数
async function loadSettings() {
  try {
    const data = await fetchSettings()
    Object.assign(storeForm, data.store || {})
    Object.assign(cashierForm, data.cashier || {})
  } catch (e) {
    ElMessage.error(e.message || '设置加载失败')
  }
}

/**
 * 保存指定分组设置
 * @param {string} group 分组名（store/cashier）
 * @param {object} form 表单对象
 * @param {string} msg 成功提示
 */
async function saveGroup(group, form, msg) {
  try {
    await saveSettings(group, { ...form })
    ElMessage.success(msg)
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  }
}

// ---------- 用户权限 ----------
// 用户列表（来自服务端）
const users = ref([])
// 新增/编辑弹窗
const userDialog = ref(false)
// 保存中状态
const userSaving = ref(false)
// 用户表单模型
const userForm = reactive({
  id: null,
  username: '',
  name: '',
  role: 'cashier',
  password: '',
  enabled: true,
})

/**
 * 服务端用户转表格行
 * @param {object} u 服务端用户
 * @returns {object} 表格行
 */
const toUserRow = (u) => ({
  id: u.id,
  username: u.username,
  name: u.name,
  role: ROLE_NAMES[u.role] || u.role,
  roleCode: u.role,
  enabled: u.enabled,
  status: u.enabled ? '启用' : '停用',
  createdAt: formatTime(u.created_at),
})

// 加载用户列表
async function loadUsers() {
  try {
    const res = await fetchUsers({ pageSize: 200 })
    users.value = (res.items || []).map(toUserRow)
  } catch (e) {
    ElMessage.error(e.message || '用户加载失败')
  }
}

// 打开新增用户弹窗
const openAddUser = () => {
  Object.assign(userForm, {
    id: null,
    username: '',
    name: '',
    role: 'cashier',
    password: '',
    enabled: true,
  })
  userDialog.value = true
}

// 打开编辑用户弹窗
const editUser = (row) => {
  Object.assign(userForm, {
    id: row.id,
    username: row.username,
    name: row.name,
    role: row.roleCode,
    password: '',
    enabled: row.enabled,
  })
  userDialog.value = true
}

// 保存新增/编辑用户到服务端
const saveUser = async () => {
  if (!userForm.name || (!userForm.id && !userForm.username)) {
    ElMessage.warning('请填写用户名和姓名')
    return
  }
  userSaving.value = true
  try {
    if (userForm.id) {
      await updateUser(userForm.id, {
        name: userForm.name,
        role: userForm.role,
        enabled: userForm.enabled,
      })
      ElMessage.success('用户已更新')
    } else {
      await createUser({
        username: userForm.username,
        name: userForm.name,
        role: userForm.role,
        password: userForm.password,
      })
      ElMessage.success(`用户「${userForm.username}」已创建`)
    }
    userDialog.value = false
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    userSaving.value = false
  }
}

// 重置密码：服务端重置为默认密码 123456
const resetPassword = (row) => {
  ElMessageBox.confirm(`确定将「${row.username}」的密码重置为 123456 吗？`, '重置密码', {
    confirmButtonText: '重置',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await resetUserPassword(row.id)
        ElMessage.success(`已重置「${row.username}」密码为 123456`)
      } catch (e) {
        ElMessage.error(e.message || '重置失败')
      }
    })
    .catch(() => {})
}

// ---------- 操作日志 ----------
// 日志列表（服务端分页）
const logs = ref([])
// 日志搜索关键字
const logKeyword = ref('')
// 日志页码
const logPage = ref(1)
// 日志总数
const logTotal = ref(0)
// 日志每页数量
const logPageSize = 20

/**
 * 加载操作日志
 * @param {number} page 页码
 */
async function loadLogs(page = 1) {
  logPage.value = page
  try {
    const res = await fetchOperationLogs({
      keyword: logKeyword.value.trim(),
      page,
      pageSize: logPageSize,
    })
    logTotal.value = res.total || 0
    logs.value = (res.items || []).map((item) => ({
      time: formatTime(item.created_at),
      operator: item.operator || 'system',
      role: ROLE_NAMES[item.role] || item.role || '系统',
      actionText: item.detail ? `${item.action}：${item.detail}` : item.action,
    }))
  } catch (e) {
    ElMessage.error(e.message || '日志加载失败')
  }
}

// 搜索日志（重置到第一页）
const searchLogs = () => loadLogs(1)

// ---------- 数据备份 ----------
// 备份文件列表
const backupHistory = ref([])

// 加载备份列表
async function loadBackups() {
  try {
    const list = await fetchBackups()
    backupHistory.value = (list || []).map((b) => ({
      name: b.name,
      time: formatTime(b.created_at),
      size: formatSize(b.size),
    }))
  } catch (e) {
    ElMessage.error(e.message || '备份列表加载失败')
  }
}

// 立即备份：调用服务端生成数据库备份
const backupNow = async () => {
  try {
    const backup = await createBackup()
    ElMessage.success(`备份已创建：${backup.name}`)
    await loadBackups()
  } catch (e) {
    ElMessage.error(e.message || '备份失败')
  }
}

// 下载备份文件
const download = (row) => {
  window.open(backupDownloadUrl(row.name), '_blank')
}

// 切换设置页签时按需加载对应数据
watch(activeMenu, (tab) => {
  if (tab === 'users') loadUsers()
  else if (tab === 'logs') loadLogs(1)
  else if (tab === 'backup') loadBackups()
})

// 页面初始化：加载设置与用户列表
onMounted(() => {
  loadSettings()
  loadUsers()
})
</script>

<style scoped>
.settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.settings-body {
  display: flex;
  gap: 8px;
  padding: 12px;
}
/* 统一卡片样式 */
.card {
  background: #fff;
  border-radius: var(--radius-md);
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--neutral-200);
}
.settings-menu {
  width: 200px;
  border-right: 1px solid var(--neutral-200) !important;
  padding-right: 8px;
}
.settings-menu :deep(.el-menu-item) {
  height: 44px;
  border-radius: 8px;
  margin-bottom: 4px;
}
.settings-menu :deep(.el-menu-item.is-active) {
  background: var(--brand-soft);
  color: var(--brand-deep);
  font-weight: 600;
}
.settings-content {
  flex: 1;
  padding: 8px 20px 20px;
  min-width: 0;
}
.section-title {
  font-size: 15px;
  color: var(--neutral-800);
  margin-bottom: 18px;
}
.setting-form :deep(.el-form-item) {
  margin-bottom: 18px;
}
.form-hint {
  margin: 0 10px;
  font-size: 12px;
  color: var(--neutral-400);
}
.content-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.content-head .section-title {
  margin-bottom: 0;
}
.content-table {
  margin-bottom: 14px;
}
.cell-time {
  font-size: 12px;
  color: var(--neutral-400);
}
/* 角色权限说明卡片 */
.perm-card {
  background: var(--neutral-50);
  border: 1px dashed var(--neutral-300);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.perm-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--neutral-700);
  margin-bottom: 10px;
}
.perm-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.perm-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--neutral-600);
}
.pager {
  margin-top: 12px;
  justify-content: flex-end;
}
/* 备份说明卡片 */
.backup-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--brand-soft);
  border: none;
  margin-bottom: 16px;
}
.card-inner {
  background: var(--brand-soft);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.tip-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--brand-deep);
}
.tip-desc {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--neutral-500);
  line-height: 1.8;
}
</style>
