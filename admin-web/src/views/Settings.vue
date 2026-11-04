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
              <el-button type="primary" @click="save('门店信息已保存')">保存设置</el-button>
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
              <el-button type="primary" @click="save('收银参数已保存')">保存设置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- ========== 用户权限 ========== -->
        <div v-show="activeMenu === 'users'">
          <div class="content-head">
            <h3 class="section-title">用户权限</h3>
            <el-button type="primary" :icon="Plus" @click="userDialog = true">新增用户</el-button>
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
            <el-table-column prop="lastLogin" label="最近登录" min-width="130" align="center">
              <template #default="{ row }"><span class="cell-time">{{ row.lastLogin }}</span></template>
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
          <!-- 新增用户弹窗 -->
          <el-dialog v-model="userDialog" title="新增用户" width="440px" destroy-on-close>
            <el-form label-width="80px">
              <el-form-item label="用户名" required>
                <el-input v-model="userForm.username" placeholder="登录账号" />
              </el-form-item>
              <el-form-item label="姓名" required>
                <el-input v-model="userForm.name" placeholder="真实姓名" />
              </el-form-item>
              <el-form-item label="角色" required>
                <el-select v-model="userForm.role" style="width: 100%">
                  <el-option label="管理员" value="管理员" />
                  <el-option label="店长" value="店长" />
                  <el-option label="收银员" value="收银员" />
                </el-select>
              </el-form-item>
              <el-form-item label="初始密码">
                <el-input v-model="userForm.password" placeholder="默认 123456" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="userDialog = false">取消</el-button>
              <el-button type="primary" @click="addUser">确认新增</el-button>
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
            />
          </div>
          <el-table :data="filteredLogs" empty-text="暂无日志记录" class="content-table">
            <el-table-column label="时间" width="150" align="right">
              <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
            </el-table-column>
            <el-table-column prop="operator" label="操作人" width="100" align="center" />
            <el-table-column prop="role" label="角色" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="roleTag(row.role)" effect="light">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action" label="操作内容" min-width="220" show-overflow-tooltip />
            <el-table-column label="结果" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.result === '成功' ? 'success' : 'danger'" effect="light">{{ row.result }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            class="pager"
            background
            layout="total, prev, pager, next"
            :total="filteredLogs.length"
            :page-size="10"
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
            <el-table-column label="类型" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.type === '自动' ? 'info' : 'warning'" effect="light">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="大小" width="100" align="right">
              <template #default="{ row }"><span class="num">{{ row.size }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
                <el-popconfirm title="恢复将覆盖当前数据，确定继续？" @confirm="restore(row)">
                  <template #reference>
                    <el-button link type="warning" size="small">恢复</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search, Refresh, Shop, Operation, User, Document, FolderChecked, InfoFilled } from '@element-plus/icons-vue'

// 当前设置子菜单
const activeMenu = ref('store')

// 通用保存提示（示意）
const save = (msg) => ElMessage.success(msg)

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

// ---------- 用户权限 ----------
// 模拟数据：用户列表
const users = ref([
  { username: 'admin', name: '张经理', role: '管理员', status: '启用', lastLogin: '2026-11-05 18:00' },
  { username: 'store01', name: '王店长', role: '店长', status: '启用', lastLogin: '2026-11-05 17:52' },
  { username: 'cashier01', name: '李收银', role: '收银员', status: '启用', lastLogin: '2026-11-05 18:10' },
  { username: 'cashier02', name: '张收银', role: '收银员', status: '启用', lastLogin: '2026-11-05 15:30' },
  { username: 'cashier03', name: '陈收银', role: '收银员', status: '停用', lastLogin: '2026-11-02 12:00' },
])

// 角色标签：管理员红 / 店长橙 / 收银员蓝
const roleTag = (r) => (r === '管理员' ? 'danger' : r === '店长' ? 'warning' : 'info')

// 新增用户弹窗
const userDialog = ref(false)
const userForm = reactive({ username: '', name: '', role: '收银员', password: '123456' })

const addUser = () => {
  if (!userForm.username || !userForm.name) {
    ElMessage.warning('请填写用户名和姓名')
    return
  }
  users.value.push({
    username: userForm.username,
    name: userForm.name,
    role: userForm.role,
    status: '启用',
    lastLogin: '——',
  })
  ElMessage.success(`用户「${userForm.username}」已创建`)
  userDialog.value = false
}

// 编辑用户（示意）
const editUser = (row) => ElMessage.info(`编辑用户「${row.username}」（示意）`)

// 重置密码（示意）
const resetPassword = (row) => {
  row.passwordReset = true
  ElMessage.success(`已重置「${row.username}」密码为 123456`)
}

// ---------- 操作日志 ----------
// 模拟数据：操作日志
const logs = ref([
  { time: '2026-11-05 18:20', operator: 'admin', role: '管理员', action: '新增促销「晚间蔬菜特价」', result: '成功' },
  { time: '2026-11-05 18:05', operator: 'cashier01', role: '收银员', action: '登记报损：上海青 2.3kg（损耗）', result: '成功' },
  { time: '2026-11-05 17:40', operator: 'store01', role: '店长', action: '创建入库单 RK20261105-003', result: '成功' },
  { time: '2026-11-05 17:22', operator: 'admin', role: '管理员', action: '修改收银参数：积分比例调整', result: '成功' },
  { time: '2026-11-05 16:50', operator: 'cashier02', role: '收银员', action: '发起盘点单 PD20261105-001', result: '成功' },
  { time: '2026-11-05 16:10', operator: 'store01', role: '店长', action: '导出销售报表（11 月）', result: '成功' },
  { time: '2026-11-05 15:00', operator: 'cashier03', role: '收银员', action: '登录失败：密码错误', result: '失败' },
  { time: '2026-11-05 14:30', operator: 'admin', role: '管理员', action: '创建用户「cashier03」', result: '成功' },
  { time: '2026-11-05 11:00', operator: 'store01', role: '店长', action: '调整商品「西红柿」售价', result: '成功' },
  { time: '2026-11-05 09:12', operator: 'admin', role: '管理员', action: '执行手动数据备份', result: '成功' },
  { time: '2026-11-04 22:00', operator: 'system', role: '系统', action: '自动备份：每日例行备份', result: '成功' },
  { time: '2026-11-04 18:30', operator: 'cashier01', role: '收银员', action: '会员充值：张**芳 +500 元', result: '成功' },
])

// 日志搜索过滤
const logKeyword = ref('')
const filteredLogs = computed(() => {
  const k = logKeyword.value.trim()
  if (!k) return logs.value
  return logs.value.filter((l) => l.operator.includes(k) || l.action.includes(k))
})

// ---------- 数据备份 ----------
// 模拟数据：备份历史
const backupHistory = ref([
  { time: '2026-11-05 02:00', type: '自动', size: '86.4 MB' },
  { time: '2026-11-05 09:12', type: '手动', size: '86.2 MB' },
  { time: '2026-11-04 02:00', type: '自动', size: '84.1 MB' },
  { time: '2026-11-03 02:00', type: '自动', size: '82.7 MB' },
  { time: '2026-11-01 10:00', type: '手动', size: '80.3 MB' },
])

// 立即备份（示意）
const backupNow = () => {
  backupHistory.value.unshift({ time: '2026-11-05 18:30', type: '手动', size: '86.5 MB' })
  ElMessage.success('备份已开始，完成后将显示在列表（示意）')
}

// 下载备份（示意）
const download = (row) => ElMessage.success(`开始下载备份文件 ${row.time}（示意）`)

// 恢复备份（示意）
const restore = (row) => ElMessage.success(`已从 ${row.time} 的备份恢复数据（示意）`)
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
