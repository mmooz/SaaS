<!-- 门店管理页面：门店列表、新增/编辑、删除与员工授权 -->
<template>
  <div class="store-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div>
        <h3 class="page-title">门店管理</h3>
        <p class="page-tip">维护当前租户的门店档案，并为员工授权可访问的门店</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增门店</el-button>
    </div>

    <!-- 门店列表 -->
    <el-table :data="stores" v-loading="loading" stripe class="store-table">
      <el-table-column prop="name" label="门店名称" min-width="160" />
      <el-table-column label="地址" min-width="200">
        <template #default="{ row }">{{ row.address || '-' }}</template>
      </el-table-column>
      <el-table-column label="联系电话" min-width="140">
        <template #default="{ row }">{{ row.phone || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" effect="light">
            {{ row.enabled ? '启用中' : '已停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="openGrant(row)">员工授权</el-button>
          <el-button link type="danger" :disabled="isCurrentStore(row)" @click="removeStore(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑门店弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑门店' : '新增门店'"
      width="480px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <el-form-item label="门店名称" prop="name">
          <el-input v-model="form.name" placeholder="如：鲜衡云总店" maxlength="100" />
        </el-form-item>
        <el-form-item label="门店地址">
          <el-input v-model="form.address" placeholder="选填" maxlength="255" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.phone" placeholder="选填" maxlength="30" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 员工授权弹窗 -->
    <el-dialog v-model="grantVisible" :title="`员工授权 · ${grantStore ? grantStore.name : ''}`" width="560px">
      <div class="grant-add">
        <el-select v-model="addUserId" placeholder="选择本租户员工" filterable class="grant-select">
          <el-option
            v-for="user in grantableUsers"
            :key="user.id"
            :label="`${user.name || user.username}（${user.username}）`"
            :value="user.id"
          />
        </el-select>
        <el-button type="primary" :disabled="!addUserId" :loading="granting" @click="grant">
          授权
        </el-button>
      </div>
      <el-table :data="grantedUsers" v-loading="grantLoading" size="small">
        <el-table-column prop="username" label="账号" min-width="120" />
        <el-table-column label="姓名" min-width="100">
          <template #default="{ row }">{{ row.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="100">
          <template #default="{ row }">{{ roleLabel(row.role) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="danger" @click="revoke(row)">撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="grantVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  clearStoreInfo,
  createStore,
  deleteStore,
  fetchStoreUsers,
  fetchStores,
  fetchUsers,
  getCurrentStore,
  grantStoreAccess,
  revokeStoreAccess,
  setCurrentStore,
  updateStore,
} from '../api'

// 门店列表数据
const stores = ref([])
// 列表加载状态
const loading = ref(false)
// 新增/编辑弹窗可见状态
const dialogVisible = ref(false)
// 是否为编辑模式（false 表示新增）
const editing = ref(false)
// 正在编辑的门店 ID
const editingId = ref(null)
// 提交中的加载状态
const submitting = ref(false)
// 表单引用
const formRef = ref(null)

// 门店表单数据
const form = reactive({
  name: '',
  address: '',
  phone: '',
  enabled: true,
})

// 表单校验规则
const rules = {
  name: [{ required: true, message: '请输入门店名称', trigger: 'blur' }],
}

// 员工授权弹窗可见状态
const grantVisible = ref(false)
// 当前正在授权的门店
const grantStore = ref(null)
// 已授权员工列表
const grantedUsers = ref([])
// 已授权员工加载状态
const grantLoading = ref(false)
// 本租户全部员工（用于下拉选择）
const tenantUsers = ref([])
// 待授权员工 ID
const addUserId = ref(null)
// 授权提交状态
const granting = ref(false)

// 可授权员工：排除已授权的员工
const grantableUsers = computed(() =>
  tenantUsers.value.filter(
    (u) => !grantedUsers.value.some((g) => String(g.id) === String(u.id)),
  ),
)

// 当前选中门店 ID（用于禁止删除正在使用的门店）
const currentStoreId = ref(getCurrentStore())

/**
 * 判断是否为当前正在使用的门店
 * @param {object} row 门店行数据
 * @returns {boolean} 是当前门店返回 true
 */
function isCurrentStore(row) {
  return String(row.id) === String(currentStoreId.value)
}

/**
 * 角色中文名称
 * @param {string} role 角色编码
 * @returns {string} 角色名称
 */
function roleLabel(role) {
  const map = { admin: '租户管理员', manager: '店长', cashier: '收银员', super: '超级管理员' }
  return map[role] || role
}

/**
 * 加载门店列表
 * @returns {Promise<void>}
 */
async function loadStores() {
  loading.value = true
  try {
    stores.value = await fetchStores()
  } catch (err) {
    ElMessage.error(`加载门店失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

/**
 * 重置表单为初始值
 * @returns {void}
 */
function resetForm() {
  Object.assign(form, { name: '', address: '', phone: '', enabled: true })
  formRef.value?.clearValidate()
}

/**
 * 打开新增门店弹窗
 * @returns {void}
 */
function openCreate() {
  editing.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

/**
 * 打开编辑门店弹窗
 * @param {object} row 门店行数据
 * @returns {void}
 */
function openEdit(row) {
  editing.value = true
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    address: row.address || '',
    phone: row.phone || '',
    enabled: row.enabled !== false,
  })
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

/**
 * 提交新增或编辑
 * @returns {Promise<void>}
 */
async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      address: form.address.trim() || null,
      phone: form.phone.trim() || null,
      enabled: form.enabled,
    }
    if (editing.value) {
      await updateStore(editingId.value, payload)
      ElMessage.success('门店信息已更新')
    } else {
      await createStore(payload)
      ElMessage.success('门店创建成功')
    }
    dialogVisible.value = false
    await loadStores()
  } catch (err) {
    ElMessage.error(`保存失败：${err.message}`)
  } finally {
    submitting.value = false
  }
}

/**
 * 删除门店（需二次确认）
 * @param {object} row 门店行数据
 * @returns {Promise<void>}
 */
async function removeStore(row) {
  try {
    await ElMessageBox.confirm(
      `删除门店「${row.name}」后将清除该门店的员工授权，是否继续？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteStore(row.id)
    ElMessage.success('门店已删除')
    await loadStores()
  } catch (err) {
    ElMessage.error(`删除失败：${err.message}`)
  }
}

/**
 * 打开员工授权弹窗并加载数据
 * @param {object} row 门店行数据
 * @returns {Promise<void>}
 */
async function openGrant(row) {
  grantStore.value = row
  addUserId.value = null
  grantVisible.value = true
  await Promise.all([loadGrantedUsers(), loadTenantUsers()])
}

/**
 * 加载已授权员工
 * @returns {Promise<void>}
 */
async function loadGrantedUsers() {
  if (!grantStore.value) return
  grantLoading.value = true
  try {
    grantedUsers.value = await fetchStoreUsers(grantStore.value.id)
  } catch (err) {
    ElMessage.error(`加载授权员工失败：${err.message}`)
  } finally {
    grantLoading.value = false
  }
}

/**
 * 加载本租户员工列表（用于授权下拉）
 * @returns {Promise<void>}
 */
async function loadTenantUsers() {
  try {
    const res = await fetchUsers({ pageSize: 100 })
    tenantUsers.value = res.items || []
  } catch (err) {
    ElMessage.error(`加载员工列表失败：${err.message}`)
  }
}

/**
 * 授权选中的员工访问当前门店
 * @returns {Promise<void>}
 */
async function grant() {
  if (!grantStore.value || !addUserId.value) return
  granting.value = true
  try {
    await grantStoreAccess(grantStore.value.id, addUserId.value)
    ElMessage.success('授权成功')
    addUserId.value = null
    await loadGrantedUsers()
  } catch (err) {
    ElMessage.error(`授权失败：${err.message}`)
  } finally {
    granting.value = false
  }
}

/**
 * 撤销员工的当前门店权限
 * @param {object} user 员工行数据
 * @returns {Promise<void>}
 */
async function revoke(user) {
  if (!grantStore.value) return
  try {
    await revokeStoreAccess(grantStore.value.id, user.id)
    ElMessage.success('已撤销授权')
    await loadGrantedUsers()
  } catch (err) {
    ElMessage.error(`撤销失败：${err.message}`)
  }
}

/**
 * 同步当前门店缓存：删除门店后若该门店为当前门店，则自动切换到剩余门店
 * @returns {void}
 */
function syncCurrentStore() {
  const current = getCurrentStore()
  const exists = stores.value.some((s) => String(s.id) === String(current))
  if (exists) return
  const first = stores.value.find((s) => s.enabled !== false)
  if (first) {
    setCurrentStore(first.id)
    currentStoreId.value = String(first.id)
  } else {
    clearStoreInfo()
    currentStoreId.value = ''
  }
}

onMounted(async () => {
  await loadStores()
  syncCurrentStore()
})
</script>

<style scoped>
.store-page {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  box-shadow: var(--shadow-sm);
}
.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-title {
  font-size: 18px;
  margin: 0 0 6px;
  color: var(--neutral-900);
}
.page-tip {
  margin: 0;
  font-size: 13px;
  color: var(--neutral-500);
}
.grant-add {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.grant-select {
  flex: 1;
}
</style>
