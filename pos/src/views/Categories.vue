<template>
  <div class="categories-page">
    <!-- 左侧：两级分类树 -->
    <div class="tree-card" v-loading="loading">
      <div class="card-head">
        <h3>商品分类</h3>
        <el-button type="primary" link size="small" @click="openAdd(null)">
          <el-icon><Plus /></el-icon>新增一级
        </el-button>
      </div>
      <el-tree
        ref="treeRef"
        :data="treeData"
        node-key="id"
        :props="treeProps"
        default-expand-all
        highlight-current
        :expand-on-click-node="false"
        @node-click="onNodeClick"
      >
        <template #default="{ data }">
          <div class="tree-node">
            <span class="node-name">{{ data.name }}</span>
            <span class="node-count num">{{ data.count }}</span>
          </div>
        </template>
      </el-tree>
    </div>

    <!-- 右侧：当前分类详情 -->
    <div class="detail-area">
      <!-- 分类信息卡片 -->
      <div class="detail-card">
        <div class="detail-head">
          <div class="detail-title">
            <h3>{{ current.name }}</h3>
            <el-tag size="small" :type="current.isRoot ? 'primary' : 'info'" effect="light">
              {{ current.isRoot ? '一级分类' : '二级分类' }}
            </el-tag>
          </div>
          <div class="detail-actions">
            <el-button v-if="current.id && current.isRoot" size="small" @click="openAdd(current)">
              <el-icon><Plus /></el-icon>新增子分类
            </el-button>
            <el-button size="small" :disabled="!current.id" @click="openEdit(current)">
              <el-icon><EditPen /></el-icon>编辑名称
            </el-button>
            <el-button size="small" type="danger" plain :disabled="!current.id" @click="handleDelete(current)">
              <el-icon><Delete /></el-icon>删除
            </el-button>
          </div>
        </div>

        <!-- 商品数量统计 -->
        <div class="stat-grid">
          <div class="stat-item">
            <div class="stat-label">在售商品</div>
            <div class="stat-value num" style="--c: var(--brand)">{{ current.onSale }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">停售商品</div>
            <div class="stat-value num" style="--c: var(--neutral-400)">{{ current.offSale }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">本月上新</div>
            <div class="stat-value num" style="--c: var(--accent)">{{ current.newThisMonth }}</div>
          </div>
        </div>

        <!-- 分类基础信息 -->
        <div class="info-list">
          <div class="info-row">
            <span class="info-label">上级分类</span>
            <span class="info-value">{{ current.parentName || '—（根分类）' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ current.createdAt }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">排序</span>
            <span class="info-value">
              <el-input-number v-model="current.sort" :min="0" :max="999" size="small" />
              <el-button size="small" class="sort-btn" @click="saveSort">保存排序</el-button>
            </span>
          </div>
        </div>
      </div>

      <!-- 空状态：未选中分类 -->
      <el-empty v-if="!current.id" description="请在左侧选择或新增分类" class="empty-card" />
    </div>

    <!-- 新增 / 编辑分类弹窗 -->
    <el-dialog v-model="addVisible" :title="addForm.id ? '编辑分类' : '新增分类'" width="420px">
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="90px">
        <el-form-item label="上级分类">
          <el-input :model-value="addForm.parentName || '（无，一级分类）'" disabled />
        </el-form-item>
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="addForm.name" placeholder="如：叶菜" maxlength="10" show-word-limit />
        </el-form-item>
        <el-form-item label="排序值" prop="sort">
          <el-input-number v-model="addForm.sort" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAdd">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, EditPen, Delete } from '@element-plus/icons-vue'
import {
  fetchCategoryTree,
  fetchProducts,
  createCategory,
  updateCategory,
  deleteCategory,
} from '../api'

// 分类树数据（节点含商品统计）
const treeData = ref([])
// 树加载状态
const loading = ref(false)

// el-tree 字段映射
const treeProps = { children: 'children', label: 'name' }

// 空分类占位（未选中或暂无分类时展示）
const emptyCategory = {
  id: null,
  name: '未选择分类',
  count: 0,
  isRoot: true,
  parentId: null,
  parentName: '',
  createdAt: '',
  onSale: 0,
  offSale: 0,
  newThisMonth: 0,
  sort: 0,
  enabled: true,
}

// 当前选中的分类节点（默认第一个一级分类）
const current = ref({ ...emptyCategory })

/**
 * 拉取全部商品（分页循环，供分类统计使用）
 * @returns {Promise<Array<object>>} 全部商品
 */
async function fetchAllProducts() {
  const all = []
  let page = 1
  while (true) {
    const res = await fetchProducts({ page, pageSize: 200 })
    const items = res.items || []
    all.push(...items)
    if (all.length >= (res.total || 0) || items.length < 200) break
    page += 1
  }
  return all
}

/**
 * 统计各分类的商品数量（在售/停售/本月上新）
 * @param {Array<object>} products 商品列表
 * @returns {object} 分类 ID -> 统计结果
 */
function buildStats(products) {
  const now = new Date()
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).getTime()
  const stats = {}
  products.forEach((p) => {
    if (p.category_id == null) return
    const s = stats[p.category_id] || (stats[p.category_id] = { total: 0, onSale: 0, offSale: 0, newThisMonth: 0 })
    s.total += 1
    if (p.enabled) s.onSale += 1
    else s.offSale += 1
    if (p.created_at && new Date(p.created_at).getTime() >= monthStart) s.newThisMonth += 1
  })
  return stats
}

/**
 * 递归构造树节点，并将子分类商品数量汇总到父节点
 * @param {object} cat 服务端分类节点
 * @param {string} parentName 上级分类名称
 * @param {object} stats 分类统计结果
 * @returns {object} 前端树节点
 */
function buildNode(cat, parentName, stats) {
  const own = stats[cat.id] || { total: 0, onSale: 0, offSale: 0, newThisMonth: 0 }
  const node = {
    id: cat.id,
    name: cat.name,
    count: own.total,
    isRoot: cat.parent_id == null,
    parentId: cat.parent_id,
    parentName,
    createdAt: (cat.created_at || '').slice(0, 10),
    onSale: own.onSale,
    offSale: own.offSale,
    newThisMonth: own.newThisMonth,
    sort: cat.sort,
    enabled: cat.enabled,
    children: [],
  }
  // 子分类递归构建并累计统计
  node.children = (cat.children || []).map((c) => buildNode(c, cat.name, stats))
  node.children.forEach((k) => {
    node.count += k.count
    node.onSale += k.onSale
    node.offSale += k.offSale
    node.newThisMonth += k.newThisMonth
  })
  return node
}

/**
 * 在树中按 ID 查找节点
 * @param {Array<object>} nodes 树节点
 * @param {number} id 分类 ID
 * @returns {object|null} 命中节点
 */
function findNode(nodes, id) {
  for (const n of nodes) {
    if (n.id === id) return n
    const hit = findNode(n.children || [], id)
    if (hit) return hit
  }
  return null
}

// 加载分类树与商品统计
async function loadData() {
  loading.value = true
  try {
    const [tree, products] = await Promise.all([fetchCategoryTree(), fetchAllProducts()])
    const stats = buildStats(products)
    treeData.value = tree.map((c) => buildNode(c, '', stats))
    // 保持原选中项，不存在时回退到第一个一级分类
    const selectedId = current.value.id
    const hit = selectedId != null ? findNode(treeData.value, selectedId) : null
    current.value = hit || treeData.value[0] || { ...emptyCategory }
  } catch (e) {
    ElMessage.error(e.message || '分类加载失败')
  } finally {
    loading.value = false
  }
}

// 点击树节点：切换右侧详情
const onNodeClick = (data) => {
  current.value = data
}

// 保存排序：写回服务端
const saveSort = async () => {
  if (!current.value.id) return
  try {
    await updateCategory(current.value.id, {
      name: current.value.name,
      parentId: current.value.parentId,
      sort: current.value.sort,
      enabled: current.value.enabled,
    })
    ElMessage.success(`已保存「${current.value.name}」的排序值 ${current.value.sort}`)
    await loadData()
  } catch (e) {
    ElMessage.error(e.message || '排序保存失败')
  }
}

// ---- 新增 / 编辑分类 ----
const addVisible = ref(false)
const addFormRef = ref(null)
// 新增 / 编辑分类表单模型
const addForm = ref({ id: null, name: '', sort: 0, parentId: null, parentName: '' })
const addRules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

// 打开新增弹窗：parent 为空表示新增一级分类
const openAdd = (parent) => {
  addForm.value = {
    id: null,
    name: '',
    sort: 0,
    parentId: parent ? parent.id : null,
    parentName: parent ? parent.name : '',
  }
  addVisible.value = true
}

// 打开编辑弹窗：回填当前分类
const openEdit = (node) => {
  if (!node.id) return
  addForm.value = {
    id: node.id,
    name: node.name,
    sort: node.sort,
    parentId: node.parentId,
    parentName: node.parentName,
  }
  addVisible.value = true
}

// 提交新增 / 编辑到服务端
const submitAdd = () => {
  addFormRef.value.validate(async (valid) => {
    if (!valid) return
    const { name, sort, parentId, id } = addForm.value
    try {
      if (id) {
        await updateCategory(id, { name, parentId, sort, enabled: true })
        ElMessage.success('分类已更新')
      } else {
        await createCategory({ name, parentId, sort, enabled: true })
        ElMessage.success(`已新增分类「${name}」`)
      }
      addVisible.value = false
      await loadData()
    } catch (e) {
      ElMessage.error(e.message || '保存失败')
    }
  })
}

// 删除分类：二次确认，服务端校验子分类/商品占用
const handleDelete = (node) => {
  if (!node.id) return
  const hasChildren = node.children && node.children.length > 0
  const tip = hasChildren
    ? `分类「${node.name}」下还有 ${node.children.length} 个子分类，需先处理子分类后才能删除。`
    : `确定删除分类「${node.name}」吗？`
  ElMessageBox.confirm(tip, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await deleteCategory(node.id)
        current.value = { ...emptyCategory }
        ElMessage.success('删除成功')
        await loadData()
      } catch (e) {
        ElMessage.error(e.message || '删除失败')
      }
    })
    .catch(() => {})
}

// 页面初始化：加载分类树
onMounted(loadData)
</script>

<style scoped>
.categories-page {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

/* 左侧分类树卡片 */
.tree-card {
  width: 300px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.card-head h3 {
  font-size: 15px;
  color: var(--neutral-800);
}
.tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 6px;
}
.node-name {
  font-size: 13px;
  color: var(--neutral-700);
}
.node-count {
  font-size: 12px;
  color: var(--neutral-400);
}
.tree-card :deep(.el-tree-node__content) {
  height: 32px;
  border-radius: 6px;
}
.tree-card :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: var(--brand-soft);
}
.tree-card :deep(.el-tree-node.is-current .node-name) {
  color: var(--brand-deep);
  font-weight: 600;
}

/* 右侧详情区 */
.detail-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.detail-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 18px;
}
.detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.detail-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.detail-title h3 {
  font-size: 17px;
  color: var(--neutral-900);
}
.detail-actions {
  display: flex;
  gap: 8px;
}

/* 商品数量统计 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-item {
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.stat-label {
  font-size: 12px;
  color: var(--neutral-500);
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--c, var(--neutral-800));
  line-height: 1.3;
}

/* 分类基础信息 */
.info-list {
  border-top: 1px solid var(--neutral-100);
  padding-top: 4px;
}
.info-row {
  display: flex;
  align-items: center;
  padding: 9px 0;
  font-size: 13px;
}
.info-label {
  width: 90px;
  color: var(--neutral-500);
}
.info-value {
  color: var(--neutral-800);
  display: flex;
  align-items: center;
  gap: 8px;
}
.sort-btn {
  margin-left: 4px;
}

/* 空状态卡片 */
.empty-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
</style>
