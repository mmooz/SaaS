<template>
  <div class="tenant-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div>
        <h3 class="page-title">租户管理</h3>
        <p class="page-tip">平台超级管理员可创建、启用/停用与维护租户信息</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增租户</el-button>
    </div>

    <!-- 租户列表 -->
    <el-table :data="tenants" v-loading="loading" stripe class="tenant-table">
      <el-table-column prop="name" label="租户名称" min-width="160" />
      <el-table-column prop="code" label="租户编码" min-width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" effect="light">
            {{ row.enabled ? '启用中' : '已停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="store_count" label="门店数" width="90" align="center" />
      <el-table-column prop="user_count" label="用户数" width="90" align="center" />
      <el-table-column label="创建时间" min-width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link :type="row.enabled ? 'warning' : 'success'" @click="toggleEnabled(row)">
            {{ row.enabled ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑租户' : '新增租户'"
      width="480px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="租户名称" prop="name">
          <el-input v-model="form.name" placeholder="如：鲜衡云商贸有限公司" maxlength="100" />
        </el-form-item>
        <el-form-item label="租户编码" prop="code">
          <el-input v-model="form.code" placeholder="唯一标识，如 tenant_a" maxlength="50" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>

        <!-- 初始管理员账号：仅新增时可选填写 -->
        <template v-if="!editing">
          <el-divider content-position="left">初始管理员（可选）</el-divider>
          <el-form-item label="登录账号">
            <el-input v-model="form.adminUsername" placeholder="留空则不创建管理员" maxlength="50" />
          </el-form-item>
          <el-form-item label="初始密码">
            <el-input v-model="form.adminPassword" placeholder="填写管理员账号时必填，至少 8 位，勿用常见弱口令" maxlength="100" />
          </el-form-item>
          <el-form-item label="管理员姓名">
            <el-input v-model="form.adminName" placeholder="如：李经理" maxlength="50" />
          </el-form-item>
          <p class="admin-tip">创建管理员时会自动生成一个名为“总店”的默认门店并完成授权</p>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  createTenant,
  fetchTenants,
  updateTenant,
} from '../api'

// 租户列表数据
const tenants = ref([])
// 列表加载状态
const loading = ref(false)
// 弹窗显示状态
const dialogVisible = ref(false)
// 是否为编辑模式（false 表示新增）
const editing = ref(false)
// 正在编辑的租户 ID
const editingId = ref(null)
// 提交中的加载状态
const submitting = ref(false)
// 表单引用
const formRef = ref(null)

// 弹窗表单数据
const form = reactive({
  name: '',
  code: '',
  enabled: true,
  adminUsername: '',
  adminPassword: '',
  adminName: '',
})

// 表单校验规则
const rules = {
  name: [{ required: true, message: '请输入租户名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入租户编码', trigger: 'blur' },
    { min: 2, max: 50, message: '编码长度为 2-50 个字符', trigger: 'blur' },
  ],
}

/**
 * 格式化时间为本地可读字符串
 * @param {string} value ISO 时间字符串
 * @returns {string} 格式化后的时间
 */
function formatTime(value) {
  if (!value) return '-'
  const d = new Date(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * 加载租户列表
 * @returns {Promise<void>}
 */
async function loadTenants() {
  loading.value = true
  try {
    tenants.value = await fetchTenants()
  } catch (err) {
    ElMessage.error(`加载租户失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

/**
 * 重置表单为初始值
 * @returns {void}
 */
function resetForm() {
  Object.assign(form, {
    name: '',
    code: '',
    enabled: true,
    adminUsername: '',
    adminPassword: '',
    adminName: '',
  })
  formRef.value?.clearValidate()
}

/**
 * 打开新增租户弹窗
 * @returns {void}
 */
function openCreate() {
  editing.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

/**
 * 打开编辑租户弹窗
 * @param {object} row 租户行数据
 * @returns {void}
 */
function openEdit(row) {
  editing.value = true
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    code: row.code,
    enabled: row.enabled,
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
    if (editing.value) {
      await updateTenant(editingId.value, {
        name: form.name,
        code: form.code,
        enabled: form.enabled,
      })
      ElMessage.success('租户信息已更新')
    } else {
      await createTenant({
        name: form.name,
        code: form.code,
        enabled: form.enabled,
        adminUsername: form.adminUsername.trim(),
        adminPassword: form.adminPassword.trim(),
        adminName: form.adminName.trim(),
      })
      ElMessage.success('租户创建成功')
    }
    dialogVisible.value = false
    await loadTenants()
  } catch (err) {
    ElMessage.error(`保存失败：${err.message}`)
  } finally {
    submitting.value = false
  }
}

/**
 * 启用/停用租户
 * @param {object} row 租户行数据
 * @returns {Promise<void>}
 */
async function toggleEnabled(row) {
  try {
    await updateTenant(row.id, { enabled: !row.enabled })
    ElMessage.success(row.enabled ? '租户已停用' : '租户已启用')
    await loadTenants()
  } catch (err) {
    ElMessage.error(`操作失败：${err.message}`)
  }
}

onMounted(loadTenants)
</script>

<style scoped>
.tenant-page {
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
.admin-tip {
  margin: 0 0 4px 96px;
  font-size: 12px;
  color: var(--neutral-500);
}
</style>
