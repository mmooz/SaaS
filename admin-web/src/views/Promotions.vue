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
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

// 当前筛选 tab（全部 / 限时特价 / 折扣 / 满减）
const filterTab = ref('all')
// 列表加载态（示意）
const loading = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)

// 促销类型对应的标签类型：限时特价橙 / 折扣主绿 / 满减成功绿
const typeTag = (t) => (t === '限时特价' ? 'warning' : t === '折扣' ? 'primary' : 'success')

// 模拟数据：促销列表
const promos = ref([
  { id: 1, name: '晚间蔬菜特价', type: '限时特价', scope: '蔬菜分类 12 个商品', benefit: '¥2.98/斤', start: '2026-11-01 18:00', end: '2026-11-30 21:00', enabled: true },
  { id: 2, name: '会员全场 9 折', type: '折扣', scope: '全场商品', benefit: '9 折', start: '2026-10-01 00:00', end: '2026-12-31 23:59', enabled: true },
  { id: 3, name: '满 50 减 5', type: '满减', scope: '全场商品', benefit: '满 ¥50 减 ¥5', start: '2026-11-01 00:00', end: '2026-11-30 23:59', enabled: true },
  { id: 4, name: '周末水果特价', type: '限时特价', scope: '水果分类 8 个商品', benefit: '¥6.99/斤', start: '2026-11-07 09:00', end: '2026-11-08 22:00', enabled: true },
  { id: 5, name: '肉品满 80 减 10', type: '满减', scope: '肉类分类商品', benefit: '满 ¥80 减 ¥10', start: '2026-11-01 00:00', end: '2026-11-15 23:59', enabled: false },
  { id: 6, name: '新人首单 8.8 折', type: '折扣', scope: '新注册会员', benefit: '8.8 折', start: '2026-09-01 00:00', end: '2026-11-30 23:59', enabled: true },
  { id: 7, name: '早餐蛋奶特价', type: '限时特价', scope: '蛋奶分类 6 个商品', benefit: '¥0.98/枚', start: '2026-11-10 06:00', end: '2026-11-20 10:00', enabled: false },
])

// 按 tab 过滤后的促销列表
const filteredPromos = computed(() =>
  filterTab.value === 'all' ? promos.value : promos.value.filter((p) => p.type === filterTab.value)
)

// 商品分组（供弹窗多选使用，模拟数据）
const productGroups = [
  {
    label: '蔬菜',
    options: [
      { value: '上海青', label: '上海青' },
      { value: '西红柿', label: '西红柿' },
      { value: '黄瓜', label: '黄瓜' },
      { value: '土豆', label: '土豆' },
    ],
  },
  {
    label: '水果',
    options: [
      { value: '蜜桔', label: '蜜桔' },
      { value: '香蕉', label: '香蕉' },
      { value: '苹果', label: '苹果' },
    ],
  },
  {
    label: '肉类',
    options: [
      { value: '五花肉', label: '五花肉' },
      { value: '前腿肉', label: '前腿肉' },
    ],
  },
]

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

// 表单校验规则
const formRules = {
  name: [{ required: true, message: '请输入促销名称', trigger: 'blur' }],
  products: [{ required: true, type: 'array', min: 1, message: '请选择适用商品', trigger: 'change' }],
  timeRange: [{ required: true, type: 'array', min: 2, message: '请选择生效时间段', trigger: 'change' }],
}

// 打开弹窗：无 row 为新增，有 row 为编辑回填
const openDialog = (row) => {
  if (row) {
    Object.assign(form, {
      id: row.id,
      type: row.type,
      name: row.name,
      products: row.scope === '全场商品' ? [] : [],
      price: row.type === '限时特价' ? Number(row.benefit.replace(/[¥斤]/g, '')) : 2.98,
      discount: row.type === '折扣' ? Number(row.benefit.replace(/折/g, '')) : 9,
      full: row.type === '满减' ? Number(row.benefit.match(/满\s*¥?(\d+)/)?.[1] ?? 50) : 50,
      reduce: row.type === '满减' ? Number(row.benefit.match(/减\s*¥?(\d+)/)?.[1] ?? 5) : 5,
      timeRange: [row.start, row.end],
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

// 保存促销（校验通过后写入列表，示意）
const savePromo = async () => {
  await formRef.value.validate()
  const timeRange = form.timeRange || []
  const benefit = form.type === '限时特价'
    ? `¥${form.price.toFixed(2)}/斤`
    : form.type === '折扣'
      ? `${form.discount} 折`
      : `满 ¥${form.full} 减 ¥${form.reduce}`
  const scope = form.products.length ? `${form.products.join('、')} 等 ${form.products.length} 个商品` : '全场商品'
  if (form.id) {
    // 编辑：更新已有行
    const row = promos.value.find((p) => p.id === form.id)
    Object.assign(row, { name: form.name, benefit, scope, start: timeRange[0], end: timeRange[1], enabled: form.enabled })
    ElMessage.success('促销已更新')
  } else {
    // 新增：插入列表头部
    promos.value.unshift({
      id: Date.now(),
      name: form.name,
      type: form.type,
      scope,
      benefit,
      start: timeRange[0],
      end: timeRange[1],
      enabled: form.enabled,
    })
    ElMessage.success('促销已创建')
  }
  dialogVisible.value = false
}

// 切换启用 / 停用
const toggleStatus = (row, val) => {
  row.enabled = val
  ElMessage.success(`已${val ? '启用' : '停用'}「${row.name}」`)
}

// 删除促销
const removePromo = (row) => {
  promos.value = promos.value.filter((p) => p.id !== row.id)
  ElMessage.success(`已删除「${row.name}」`)
}

// tab 切换（示意加载）
const handleFilter = () => {
  loading.value = true
  setTimeout(() => (loading.value = false), 300)
}
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
