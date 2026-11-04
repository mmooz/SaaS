<template>
  <div class="categories-page">
    <!-- 左侧：两级分类树 -->
    <div class="tree-card">
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
            <el-button v-if="!current.isRoot" size="small" @click="openAdd(current)">
              <el-icon><Plus /></el-icon>新增子分类
            </el-button>
            <el-button size="small" @click="editVisible = true">
              <el-icon><EditPen /></el-icon>编辑名称
            </el-button>
            <el-button size="small" type="danger" plain @click="handleDelete(current)">
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
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, EditPen, Delete } from '@element-plus/icons-vue'

// ---- 模拟数据：分类树（两级） ----
// 每个分类节点携带商品数统计信息
const treeData = ref([
  {
    id: 'veg', name: '蔬菜', count: 38, isRoot: true, parentName: '', createdAt: '2025-06-01', onSale: 35, offSale: 3, newThisMonth: 5, sort: 1,
    children: [
      { id: 'veg-leaf', name: '叶菜', count: 12, isRoot: false, parentName: '蔬菜', createdAt: '2025-06-01', onSale: 11, offSale: 1, newThisMonth: 2, sort: 1 },
      { id: 'veg-root', name: '根茎', count: 9, isRoot: false, parentName: '蔬菜', createdAt: '2025-06-01', onSale: 9, offSale: 0, newThisMonth: 1, sort: 2 },
      { id: 'veg-fruit', name: '茄果', count: 8, isRoot: false, parentName: '蔬菜', createdAt: '2025-06-10', onSale: 7, offSale: 1, newThisMonth: 1, sort: 3 },
      { id: 'veg-mushroom', name: '菌菇', count: 5, isRoot: false, parentName: '蔬菜', createdAt: '2025-07-02', onSale: 5, offSale: 0, newThisMonth: 0, sort: 4 },
      { id: 'veg-bean', name: '豆类', count: 4, isRoot: false, parentName: '蔬菜', createdAt: '2025-07-15', onSale: 3, offSale: 1, newThisMonth: 1, sort: 5 },
    ],
  },
  {
    id: 'fruit', name: '水果', count: 28, isRoot: true, parentName: '', createdAt: '2025-06-01', onSale: 27, offSale: 1, newThisMonth: 4, sort: 2,
    children: [
      { id: 'fruit-citrus', name: '柑橘', count: 6, isRoot: false, parentName: '水果', createdAt: '2025-06-01', onSale: 6, offSale: 0, newThisMonth: 1, sort: 1 },
      { id: 'fruit-berry', name: '浆果', count: 5, isRoot: false, parentName: '水果', createdAt: '2025-06-05', onSale: 5, offSale: 0, newThisMonth: 1, sort: 2 },
      { id: 'fruit-stone', name: '核果', count: 4, isRoot: false, parentName: '水果', createdAt: '2025-06-12', onSale: 4, offSale: 0, newThisMonth: 0, sort: 3 },
      { id: 'fruit-melon', name: '瓜类', count: 5, isRoot: false, parentName: '水果', createdAt: '2025-07-01', onSale: 5, offSale: 0, newThisMonth: 2, sort: 4 },
      { id: 'fruit-tropical', name: '热带', count: 8, isRoot: false, parentName: '水果', createdAt: '2025-08-10', onSale: 7, offSale: 1, newThisMonth: 0, sort: 5 },
    ],
  },
  {
    id: 'meat', name: '肉类', count: 18, isRoot: true, parentName: '', createdAt: '2025-06-01', onSale: 17, offSale: 1, newThisMonth: 2, sort: 3,
    children: [
      { id: 'meat-pork', name: '猪肉', count: 6, isRoot: false, parentName: '肉类', createdAt: '2025-06-01', onSale: 6, offSale: 0, newThisMonth: 1, sort: 1 },
      { id: 'meat-beef', name: '牛肉', count: 3, isRoot: false, parentName: '肉类', createdAt: '2025-06-18', onSale: 3, offSale: 0, newThisMonth: 0, sort: 2 },
      { id: 'meat-poultry', name: '禽肉', count: 5, isRoot: false, parentName: '肉类', createdAt: '2025-07-01', onSale: 4, offSale: 1, newThisMonth: 1, sort: 3 },
      { id: 'meat-lamb', name: '羊肉', count: 2, isRoot: false, parentName: '肉类', createdAt: '2025-07-20', onSale: 2, offSale: 0, newThisMonth: 0, sort: 4 },
      { id: 'meat-other', name: '其他', count: 2, isRoot: false, parentName: '肉类', createdAt: '2025-08-05', onSale: 2, offSale: 0, newThisMonth: 0, sort: 5 },
    ],
  },
  {
    id: 'aquatic', name: '水产', count: 12, isRoot: true, parentName: '', createdAt: '2025-06-01', onSale: 11, offSale: 1, newThisMonth: 1, sort: 4,
    children: [
      { id: 'aquatic-fresh', name: '淡水鱼', count: 5, isRoot: false, parentName: '水产', createdAt: '2025-06-01', onSale: 5, offSale: 0, newThisMonth: 1, sort: 1 },
      { id: 'aquatic-sea', name: '海鲜', count: 4, isRoot: false, parentName: '水产', createdAt: '2025-06-22', onSale: 3, offSale: 1, newThisMonth: 0, sort: 2 },
      { id: 'aquatic-shrimp', name: '虾蟹', count: 3, isRoot: false, parentName: '水产', createdAt: '2025-07-10', onSale: 3, offSale: 0, newThisMonth: 0, sort: 3 },
    ],
  },
  {
    id: 'grocery', name: '粮油副食', count: 24, isRoot: true, parentName: '', createdAt: '2025-06-01', onSale: 23, offSale: 1, newThisMonth: 2, sort: 5,
    children: [
      { id: 'grocery-rice', name: '米面', count: 6, isRoot: false, parentName: '粮油副食', createdAt: '2025-06-01', onSale: 6, offSale: 0, newThisMonth: 1, sort: 1 },
      { id: 'grocery-oil', name: '食用油', count: 4, isRoot: false, parentName: '粮油副食', createdAt: '2025-06-08', onSale: 4, offSale: 0, newThisMonth: 0, sort: 2 },
      { id: 'grocery-seasoning', name: '调味品', count: 5, isRoot: false, parentName: '粮油副食', createdAt: '2025-06-15', onSale: 5, offSale: 0, newThisMonth: 1, sort: 3 },
      { id: 'grocery-dry', name: '干货', count: 4, isRoot: false, parentName: '粮油副食', createdAt: '2025-07-01', onSale: 3, offSale: 1, newThisMonth: 0, sort: 4 },
      { id: 'grocery-egg', name: '蛋品', count: 5, isRoot: false, parentName: '粮油副食', createdAt: '2025-07-12', onSale: 5, offSale: 0, newThisMonth: 0, sort: 5 },
    ],
  },
])

const treeProps = { children: 'children', label: 'name' }

// 当前选中的分类节点（默认选中第一个一级分类）
const current = ref(treeData.value[0])

// 点击树节点：切换右侧详情
const onNodeClick = (data) => {
  current.value = data
}

// 保存排序：模拟提示
const saveSort = () => {
  ElMessage.success(`已保存「${current.value.name}」的排序值 ${current.value.sort}`)
}

// ---- 新增 / 编辑分类 ----
const addVisible = ref(false)
const addFormRef = ref(null)
// 新增 / 编辑分类表单模型
const addForm = ref({ id: '', name: '', sort: 0, parentId: null, parentName: '' })
const addRules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

// 打开新增弹窗：parent 为空表示新增一级分类
const openAdd = (parent) => {
  addForm.value = {
    id: '', name: '', sort: 0,
    parentId: parent ? parent.id : null,
    parentName: parent ? parent.name : '',
  }
  addVisible.value = true
}

// 提交新增 / 编辑：模拟保存到树中
const submitAdd = () => {
  addFormRef.value.validate((valid) => {
    if (!valid) return
    const { name, sort, parentId, id } = addForm.value
    const isEdit = !!id
    if (isEdit) {
      // 编辑：更新当前选中节点名称与排序
      current.value.name = name
      current.value.sort = sort
      ElMessage.success('分类已更新')
    } else if (parentId) {
      // 新增二级分类：挂到父节点下
      const parent = treeData.value.find((n) => n.id === parentId) || current.value
      const newId = `${parent.id}-${name}`
      parent.children = parent.children || []
      parent.children.push({
        id: newId, name, count: 0, isRoot: false, parentName: parent.name,
        createdAt: '2026-11-05', onSale: 0, offSale: 0, newThisMonth: 0, sort,
      })
      ElMessage.success(`已新增二级分类「${name}」`)
    } else {
      // 新增一级分类：追加到树末尾
      const newId = `cate-${Date.now()}`
      treeData.value.push({
        id: newId, name, count: 0, isRoot: true, parentName: '',
        createdAt: '2026-11-05', onSale: 0, offSale: 0, newThisMonth: 0, sort, children: [],
      })
      ElMessage.success(`已新增一级分类「${name}」`)
    }
    addVisible.value = false
  })
}

// 删除分类：二次确认（含子分类 / 商品数校验提示）
const handleDelete = (node) => {
  const hasChildren = node.children && node.children.length > 0
  const tip = hasChildren
    ? `分类「${node.name}」下还有 ${node.children.length} 个子分类，删除后子分类将一并删除。`
    : `确定删除分类「${node.name}」吗？删除后其下商品将归属「未分类」。`
  ElMessageBox.confirm(tip, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      if (node.isRoot) {
        treeData.value = treeData.value.filter((n) => n.id !== node.id)
      } else {
        // 从父节点 children 中移除
        const parent = treeData.value.find((n) => n.children && n.children.some((c) => c.id === node.id))
        if (parent) parent.children = parent.children.filter((c) => c.id !== node.id)
      }
      // 删除后回退到第一个一级分类
      current.value = treeData.value[0]
      ElMessage.success('删除成功')
    })
    .catch(() => {})
}
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
