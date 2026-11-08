<template>
  <div class="promotions">
    <!-- 页头：筛选 tab + 新增按钮 -->
    <div class="page-head card">
      <el-radio-group v-model="filterTab" @change="handleFilter">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="限时特价">限时特价</el-radio-button>
        <el-radio-button value="折扣">折扣</el-radio-button>
        <el-radio-button value="满减">满减满赠</el-radio-button>
      </el-radio-group>
      <el-button type="primary" :icon="Plus" @click="openDialog()">新增促销</el-button>
    </div>

    <!-- 促销列表卡片 -->
    <div class="card">
      <div class="card-head">
        <h3>促销列表</h3>
        <span class="list-count">共 {{ filteredPromos.length }} 条</span>
      </div>
      <el-table :data="filteredPromos" v-loading="loading" empty-text="暂无促销活动">
        <el-table-column prop="name" label="促销名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="typeTag(row.type)" effect="light">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="适用范围" width="140" align="center">
          <template #default="{ row }">{{ row.scope }}</template>
        </el-table-column>
        <el-table-column label="优惠内容" min-width="150" align="center">
          <template #default="{ row }">
            <span class="num benefit">{{ row.benefit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="生效时间" min-width="200" align="center">
          <template #default="{ row }">
            <span class="cell-time">{{ row.start }} ~ {{ row.end }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.enabled"
              @change="(v) => toggleStatus(row, v)"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="删除后不可恢复，确定删除该促销？" @confirm="removePromo(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增/编辑促销弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑促销' : '新增促销'" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="96px">
        <el-form-item label="促销类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio value="限时特价">限时特价</el-radio>
            <el-radio value="折扣">折扣</el-radio>
            <el-radio value="满减">满减</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="促销名称" prop="name">
          <el-input v-model="form.name" placeholder="如：晚间蔬菜特价" maxlength="30" show-word-limit />
        </el-form-item>
        <el-form-item label="适用商品" prop="products">
          <el-select
            v-model="form.products"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择商品（可多选）"
            style="width: 100%"
          >
            <el-option-group v-for="group in productGroups" :key="group.label" :label="group.label">
              <el-option v-for="item in group.options" :key="item.value" :label="item.label" :value="item.value" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <!-- 按促销类型切换优惠内容输入 -->
        <el-form-item v-if="form.type === '限时特价'" label="特价价格" prop="price">
          <el-input-number v-model="form.price" :min="0.01" :precision="2" :step="0.1" style="width: 200px" />
          <span class="unit-hint">元 / 斤</span>
        </el-form-item>
        <el-form-item v-else-if="form.type === '折扣'" label="折扣率" prop="discount">
          <el-input-number v-model="form.discount" :min="0.1" :max="9.9" :precision="1" :step="0.1" style="width: 200px" />
          <span class="unit-hint">折（如 9 折）</span>
        </el-form-item>
        <el-form-item v-else label="满减规则" prop="fullReduce">
          <div class="full-reduce">
            满
            <el-input-number v-model="form.full" :min="1" :precision="2" :step="5" style="width: 120px" />
            元 减
            <el-input-number v-model="form.reduce" :min="1" :precision="2" :step="1" style="width: 120px" />
            元
          </div>
        </el-form-item>
        <el-form-item label="生效时间" prop="timeRange">
          <el-date-picker
            v-model="form.timeRange"
            type="datetimerange"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.enabled" inline-prompt active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePromo">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  createPromotion,
  deletePromotion,
  fetchCategories,
  fetchProducts,
  fetchPromotions,
  updatePromotion,
} from '../api'

// 后端类型与页面文案映射
const TYPE_TO_TEXT = { special: '限时特价', discount: '折扣', full_reduce: '满减' }
const TEXT_TO_TYPE = { 限时特价: 'special', 折扣: 'discount', 满减: 'full_reduce' }

// 当前筛选 tab（全部 / 限时特价 / 折扣 / 满减）
const filterTab = ref('all')
// 列表加载态
const loading = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)

// 促销类型对应的标签类型：限时特价橙 / 折扣主绿 / 满减成功绿
const typeTag = (t) => (t === '限时特价' ? 'warning' : t === '折扣' ? 'primary' : 'success')

// 促销列表（来自后端，已转换为展示模型）
const promos = ref([])

/**
 * 时间格式化（后端 ISO 时间 → YYYY-MM-DD HH:mm）
 * @param {string|null} value ISO 时间
 * @returns {string} 展示时间
 */
function fmtTime(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 16)
}

/**
 * 后端促销转列表展示模型
 * @param {object} promo 后端促销
 * @returns {object} 展示数据
 */
function toRow(promo) {
  const params = promo.params || {}
  // 优惠内容文案
  const benefit =
    promo.type === 'special'
      ? `¥${Number(params.price || 0).toFixed(2)}`
      : promo.type === 'discount'
        ? `${(Number(params.rate || 0) * 10).toFixed(1)} 折`
        : `满 ¥${params.threshold || 0} 减 ¥${params.reduce || 0}`
  // 适用范围文案
  const scope = promo.product_ids?.length
    ? `${promo.product_ids.length} 个指定商品`
    : promo.category_ids?.length
      ? `${promo.category_ids.length} 个指定分类`
      : '全场商品'
  return {
    id: promo.id,
    name: promo.name,
    type: TYPE_TO_TEXT[promo.type] || promo.type,
    scope,
    benefit,
    start: fmtTime(promo.start_at),
    end: fmtTime(promo.end_at),
    enabled: promo.enabled,
    raw: promo,
  }
}

/**
 * 加载促销列表
 * @returns {Promise<void>}
 */
async function loadPromos() {
  loading.value = true
  try {
    const rows = await fetchPromotions()
    promos.value = rows.map(toRow)
  } catch (err) {
    ElMessage.error(`促销加载失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

// 按 tab 过滤后的促销列表
const filteredPromos = computed(() =>
  filterTab.value === 'all' ? promos.value : promos.value.filter((p) => p.type === filterTab.value),
)

// 商品分组（供弹窗多选使用，来自后端商品与分类）
const productGroups = ref([])

/**
 * 加载商品选项并按分类分组
 * @returns {Promise<void>}
 */
async function loadProductGroups() {
  try {
    const [products, tree] = await Promise.all([fetchProducts(), fetchCategories()])
    // 扁平化分类树，得到 ID → 名称
    const cateMap = {}
    const walk = (nodes) => nodes.forEach((n) => {
      cateMap[n.id] = n.name
      if (n.children?.length) walk(n.children)
    })
    walk(tree || [])
    const groups = new Map()
    for (const p of products.items || []) {
      const label = cateMap[p.category_id] || '其他'
      if (!groups.has(label)) groups.set(label, [])
      groups.get(label).push({ value: p.id, label: p.name })
    }
    productGroups.value = [...groups.entries()].map(([label, options]) => ({ label, options }))
  } catch (err) {
    ElMessage.error(`商品选项加载失败：${err.message}`)
  }
}

onMounted(() => {
  loadPromos()
  loadProductGroups()
})

// 弹窗表单（新增 / 编辑共用）
const formRef = ref(null)
const form = reactive({
  id: null,
  type: '限时特价',
  name: '',
  products: [],
  price: 2.98,
  discount: 9,
  full: 50,
  reduce: 5,
  timeRange: [],
  enabled: true,
})

// 表单校验规则（适用商品可留空表示全场）
const formRules = {
  name: [{ required: true, message: '请输入促销名称', trigger: 'blur' }],
}

// 打开弹窗：无 row 为新增，有 row 为编辑回填
const openDialog = (row) => {
  if (row) {
    const raw = row.raw || {}
    const params = raw.params || {}
    Object.assign(form, {
      id: row.id,
      type: row.type,
      name: row.name,
      products: raw.product_ids || [],
      price: row.type === '限时特价' ? Number(params.price || 2.98) : 2.98,
      discount: row.type === '折扣' ? Number(params.rate || 0.9) * 10 : 9,
      full: row.type === '满减' ? Number(params.threshold || 50) : 50,
      reduce: row.type === '满减' ? Number(params.reduce || 5) : 5,
      timeRange: raw.start_at && raw.end_at ? [fmtTime(raw.start_at), fmtTime(raw.end_at)] : [],
      enabled: row.enabled,
    })
  } else {
    Object.assign(form, {
      id: null, type: '限时特价', name: '', products: [],
      price: 2.98, discount: 9, full: 50, reduce: 5,
      timeRange: [], enabled: true,
    })
  }
  dialogVisible.value = true
}

/**
 * 表单转后端请求体
 * @returns {object} 促销请求数据
 */
function buildPayload() {
  const type = TEXT_TO_TYPE[form.type]
  const params =
    type === 'special'
      ? { price: form.price }
      : type === 'discount'
        ? { rate: +(form.discount / 10).toFixed(2) }
        : { threshold: form.full, reduce: form.reduce }
  const [start, end] = form.timeRange || []
  return {
    type,
    name: form.name,
    product_ids: form.products.length ? form.products : null,
    params,
    // 统一转为 ISO 格式（后端按 datetime 解析）
    start_at: start ? `${start.replace(' ', 'T')}:00` : null,
    end_at: end ? `${end.replace(' ', 'T')}:00` : null,
    enabled: form.enabled,
  }
}

// 保存促销（调用后端新增或更新）
const savePromo = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  const payload = buildPayload()
  try {
    if (form.id) {
      await updatePromotion(form.id, payload)
      ElMessage.success('促销已更新')
    } else {
      await createPromotion(payload)
      ElMessage.success('促销已创建')
    }
    dialogVisible.value = false
    await loadPromos()
  } catch (err) {
    ElMessage.error(`保存失败：${err.message}`)
  }
}

// 切换启用 / 停用
const toggleStatus = async (row, val) => {
  try {
    await updatePromotion(row.id, { enabled: val })
    row.enabled = val
    ElMessage.success(`已${val ? '启用' : '停用'}「${row.name}」`)
  } catch (err) {
    ElMessage.error(`操作失败：${err.message}`)
    await loadPromos()
  }
}

// 删除促销
const removePromo = async (row) => {
  try {
    await deletePromotion(row.id)
    promos.value = promos.value.filter((p) => p.id !== row.id)
    ElMessage.success(`已删除「${row.name}」`)
  } catch (err) {
    ElMessage.error(`删除失败：${err.message}`)
  }
}

// tab 切换（客户端过滤，无需请求）
const handleFilter = () => {}
</script>

<style scoped>
.promotions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
/* 统一卡片样式：白底、圆角、轻阴影 */
.card {
  background: #fff;
  border-radius: var(--radius-md);
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--neutral-200);
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.card-head h3 {
  font-size: 15px;
  color: var(--neutral-800);
}
.list-count {
  font-size: 12px;
  color: var(--neutral-400);
}
.benefit {
  color: var(--accent);
  font-weight: 600;
}
.cell-time {
  font-size: 12px;
  color: var(--neutral-500);
}
.unit-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--neutral-400);
}
.full-reduce {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--neutral-600);
}
</style>
