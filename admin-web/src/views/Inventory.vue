<template>
  <div class="inventory">
    <!-- 顶部 tab：库存查询 / 采购入库 / 盘点 / 报损 / 变动流水 -->
    <div class="card tab-bar">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="库存查询" name="query" />
        <el-tab-pane label="采购入库" name="purchase" />
        <el-tab-pane label="盘点" name="check" />
        <el-tab-pane label="报损" name="loss" />
        <el-tab-pane label="变动流水" name="flow" />
      </el-tabs>
    </div>

    <!-- ========== 1. 库存查询 ========== -->
    <div v-show="activeTab === 'query'" class="card">
      <div class="card-head">
        <h3>库存列表</h3>
        <div class="head-actions">
          <el-input
            v-model="queryKeyword"
            placeholder="搜索商品 / 条码"
            clearable
            :prefix-icon="Search"
            style="width: 240px"
            @keyup.enter="handleStockSearch"
            @clear="handleStockSearch"
          />
          <el-button type="primary" :icon="Refresh" @click="refreshAll">刷新库存</el-button>
        </div>
      </div>
      <el-table :data="stocks" v-loading="loading" empty-text="暂无库存数据">
        <el-table-column prop="name" label="商品" min-width="140" show-overflow-tooltip />
        <el-table-column prop="barcode" label="条码" width="130" />
        <el-table-column prop="category" label="分类" width="100" align="center" />
        <el-table-column label="库存" width="110" align="right">
          <template #default="{ row }">
            <span class="num" :class="{ 'text-danger': row.status !== 'ok' }">{{ row.stock }}</span>
          </template>
        </el-table-column>
        <el-table-column label="安全库存" width="110" align="right">
          <template #default="{ row }"><span class="num">{{ row.safety_stock }}</span></template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="stockTagType(row.status)" effect="light">{{ stockText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="150" align="right">
          <template #default="{ row }"><span class="cell-time">{{ fmtTime(row.updated_at) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openPurchaseDialog(row)">入库</el-button>
            <el-button link type="warning" size="small" @click="openLossDialog(row)">报损</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="stockPage"
          v-model:page-size="stockPageSize"
          :total="stockTotal"
          :page-sizes="[20, 50, 100]"
          layout="total, prev, pager, next"
          background
          @current-change="loadInventory"
          @size-change="handleStockSearch"
        />
      </div>
    </div>

    <!-- ========== 2. 采购入库 ========== -->
    <div v-show="activeTab === 'purchase'" class="card">
      <div class="card-head">
        <h3>入库单列表</h3>
        <el-button type="primary" :icon="Plus" @click="openPurchaseDialog()">新建入库单</el-button>
      </div>
      <el-table :data="inboundRecords" empty-text="暂无入库记录">
        <el-table-column label="时间" width="150">
          <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column prop="product" label="商品" min-width="150" />
        <el-table-column label="入库数量" width="120" align="right">
          <template #default="{ row }"><span class="num text-success">+{{ row.qty }}{{ row.unit }}</span></template>
        </el-table-column>
        <el-table-column label="来源" width="130" align="center">
          <template #default="{ row }"><span class="cell-time">{{ row.refNo }}</span></template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ========== 3. 盘点 ========== -->
    <div v-show="activeTab === 'check'" class="card">
      <div class="card-head">
        <h3>盘点记录</h3>
        <el-button type="primary" :icon="Plus" @click="openCheckDialog()">新建盘点单</el-button>
      </div>
      <el-table :data="stocktakeRecords" empty-text="暂无盘点记录">
        <el-table-column label="时间" width="150">
          <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column prop="product" label="商品" min-width="150" />
        <el-table-column label="差异数量" width="120" align="right">
          <template #default="{ row }">
            <span class="num" :class="row.qty > 0 ? 'text-success' : row.qty < 0 ? 'text-danger' : ''">
              {{ row.qty > 0 ? '+' : '' }}{{ row.qty }}{{ row.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作人" width="100" align="center">
          <template #default="{ row }">{{ row.operator }}</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ========== 4. 报损 ========== -->
    <div v-show="activeTab === 'loss'" class="card">
      <div class="card-head">
        <h3>报损记录</h3>
        <el-button type="primary" :icon="Plus" @click="openLossDialog()">报损登记</el-button>
      </div>
      <el-table :data="breakageRecords" empty-text="暂无报损记录">
        <el-table-column label="时间" width="150">
          <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column prop="product" label="商品" min-width="150" />
        <el-table-column label="报损数量" width="120" align="right">
          <template #default="{ row }"><span class="num text-danger">{{ Math.abs(row.qty) }}{{ row.unit }}</span></template>
        </el-table-column>
        <el-table-column label="操作人" width="100" align="center">
          <template #default="{ row }">{{ row.operator }}</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ========== 5. 变动流水 ========== -->
    <div v-show="activeTab === 'flow'" class="card">
      <div class="card-head">
        <h3>库存变动流水</h3>
        <el-input
          v-model="flowKeyword"
          placeholder="搜索商品 / 单号"
          clearable
          :prefix-icon="Search"
          style="width: 240px"
        />
      </div>
      <el-table :data="filteredFlows" empty-text="暂无变动记录">
        <el-table-column label="时间" width="150" align="right">
          <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column prop="product" label="商品" min-width="130" />
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="flowTypeTag(row.typeCode)" effect="light">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="110" align="right">
          <template #default="{ row }">
            <span class="num" :class="row.qty > 0 ? 'text-success' : 'text-danger'">
              {{ row.qty > 0 ? '+' : '' }}{{ row.qty }}{{ row.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="140" align="center">
          <template #default="{ row }"><span class="cell-time">{{ row.refNo }}</span></template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ========== 采购入库弹窗 ========== -->
    <el-dialog v-model="purchaseDialog" title="新建入库单" width="640px" destroy-on-close>
      <div class="dialog-tip">选择商品并填写进货数量与进价，可添加多行商品明细。</div>
      <el-table :data="purchaseItems" empty-text="请添加入库商品" class="dialog-table">
        <el-table-column label="商品" width="200">
          <template #default="{ row }">
            <el-select v-model="row.productId" filterable placeholder="选择商品" size="small">
              <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.qty" :min="0.01" :precision="2" :step="1" size="small" style="width: 120px" />
          </template>
        </el-table-column>
        <el-table-column label="进价(元)" width="150">
          <template #default="{ row }">
            <el-input-number v-model="row.price" :min="0.01" :precision="2" :step="0.1" size="small" style="width: 130px" />
          </template>
        </el-table-column>
        <el-table-column label="小计" width="90" align="right">
          <template #default="{ row }">
            <span class="num">¥{{ (row.qty * row.price).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column width="60" align="center">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" :icon="Delete" @click="purchaseItems.splice($index, 1)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="dialog-footer">
        <span class="total-hint num">合计 ¥{{ purchaseTotal.toFixed(2) }}</span>
        <div>
          <el-button @click="addPurchaseRow">添加商品</el-button>
          <el-button type="primary" @click="submitPurchase">提交入库</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- ========== 盘点弹窗 ========== -->
    <el-dialog v-model="checkDialog" title="新建盘点单" width="640px" destroy-on-close>
      <div class="dialog-tip">填写账面数与实盘数，系统自动计算差异（实盘 - 账面）。</div>
      <el-table :data="checkItems" empty-text="请添加盘点商品" class="dialog-table">
        <el-table-column label="商品" width="200">
          <template #default="{ row }">
            <el-select v-model="row.productId" filterable placeholder="选择商品" size="small">
              <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="账面数" width="120" align="right">
          <template #default="{ row }"><span class="num">{{ productStock(row.productId) }}</span></template>
        </el-table-column>
        <el-table-column label="实盘数" width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.actual" :min="0" :precision="2" :step="1" size="small" style="width: 120px" />
          </template>
        </el-table-column>
        <el-table-column label="差异" width="100" align="right">
          <template #default="{ row }">
            <span class="num" :class="row.actual - productStock(row.productId) === 0 ? '' : row.actual - productStock(row.productId) > 0 ? 'text-success' : 'text-danger'">
              {{ row.actual - productStock(row.productId) > 0 ? '+' : '' }}{{ (row.actual - productStock(row.productId)).toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column width="60" align="center">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" :icon="Delete" @click="checkItems.splice($index, 1)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="dialog-footer">
        <span class="total-hint">共 <span class="num">{{ checkItems.length }}</span> 个商品</span>
        <div>
          <el-button @click="addCheckRow">添加商品</el-button>
          <el-button type="primary" @click="submitCheck">提交盘点</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- ========== 报损登记弹窗 ========== -->
    <el-dialog v-model="lossDialog" title="报损登记" width="480px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="商品" required>
          <el-select v-model="lossForm.productId" filterable placeholder="选择商品" style="width: 100%">
            <el-option v-for="p in products" :key="p.id" :label="`${p.name}（库存 ${p.stock}${p.unit}）`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="lossForm.qty" :min="0.01" :precision="2" :step="1" style="width: 200px" />
        </el-form-item>
        <el-form-item label="原因">
          <el-radio-group v-model="lossForm.reason">
            <el-radio value="损耗">损耗</el-radio>
            <el-radio value="过期">过期</el-radio>
            <el-radio value="损坏">损坏</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="lossForm.note" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="lossDialog = false">取消</el-button>
        <el-button type="danger" @click="submitLoss">确认报损</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Search, Refresh } from '@element-plus/icons-vue'
import {
  fetchInventory,
  fetchInventoryMovements,
  fetchProducts,
  inventoryBreakage,
  inventoryInbound,
  inventoryStocktake,
} from '../api'

// 当前激活的 tab
const activeTab = ref('query')
// 库存列表加载态
const loading = ref(false)

/**
 * 时间格式化（ISO → YYYY-MM-DD HH:mm）
 * @param {string|null} value 时间
 * @returns {string} 展示时间
 */
function fmtTime(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 16)
}

/**
 * 数值保留三位小数
 * @param {number} n 原值
 * @returns {number} 保留三位后的数值
 */
const round3 = (n) => Math.round(n * 1000) / 1000

// 库存状态：后端值 → 中文文案
const STATUS_TO_TEXT = { out: '紧缺', low: '不足', ok: '充足' }

/**
 * 库存状态转中文
 * @param {string} s 后端状态值
 * @returns {string} 中文状态
 */
const stockText = (s) => STATUS_TO_TEXT[s] || s

// 库存状态标签：充足绿 / 不足橙 / 紧缺红
const stockTagType = (s) => (s === 'ok' ? 'success' : s === 'low' ? 'warning' : 'danger')

// 流水类型：后端值 → 中文文案
const FLOW_TYPE_TO_TEXT = { inbound: '入库', sale: '销售', stocktake: '盘点', breakage: '报损' }

/**
 * 流水类型标签颜色
 * @param {string} t 后端类型
 * @returns {string} el-tag 类型
 */
const flowTypeTag = (t) =>
  t === 'inbound' ? 'success' : t === 'sale' ? 'primary' : t === 'stocktake' ? 'warning' : 'danger'

/* ---------------- 商品选项 ---------------- */

// 商品列表（下拉与盘点账面数使用）
const products = ref([])

/**
 * 加载商品列表
 * @returns {Promise<void>}
 */
async function loadProducts() {
  try {
    const data = await fetchProducts()
    products.value = data.items || []
  } catch (err) {
    ElMessage.error(`商品加载失败：${err.message}`)
  }
}

/**
 * 按商品 ID 取商品
 * @param {number} id 商品 ID
 * @returns {object|null} 商品
 */
const productById = (id) => products.value.find((p) => p.id === id) || null

/**
 * 按商品 ID 取当前库存数
 * @param {number} id 商品 ID
 * @returns {number} 库存数
 */
const productStock = (id) => Number(productById(id)?.stock || 0)

/* ---------------- 库存查询 ---------------- */

// 搜索关键字
const queryKeyword = ref('')
// 库存列表
const stocks = ref([])
// 当前页码
const stockPage = ref(1)
// 每页条数
const stockPageSize = ref(20)
// 库存总数
const stockTotal = ref(0)

/**
 * 加载库存分页数据
 * @returns {Promise<void>}
 */
async function loadInventory() {
  loading.value = true
  try {
    const data = await fetchInventory({
      keyword: queryKeyword.value,
      page: stockPage.value,
      pageSize: stockPageSize.value,
    })
    stocks.value = data.items || []
    stockTotal.value = data.total || 0
  } catch (err) {
    ElMessage.error(`库存加载失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

/**
 * 搜索库存：重置到第一页后加载
 */
function handleStockSearch() {
  stockPage.value = 1
  loadInventory()
}

/* ---------------- 库存流水 ---------------- */

// 入库记录
const inboundRecords = ref([])
// 盘点记录
const stocktakeRecords = ref([])
// 报损记录
const breakageRecords = ref([])
// 全部变动流水
const flows = ref([])

/**
 * 库存流水转展示行
 * @param {object} m 后端流水
 * @returns {object} 展示行
 */
function toFlowRow(m) {
  const product = productById(m.product_id)
  return {
    id: m.id,
    time: fmtTime(m.created_at),
    product: m.product_name || '—',
    type: FLOW_TYPE_TO_TEXT[m.type] || m.type,
    typeCode: m.type,
    qty: round3(Number(m.weight_kg ?? m.qty ?? 0)),
    unit: product?.unit || '',
    refNo: m.ref_id ? `#${m.ref_id}` : '—',
    operator: m.operator_id ? `操作员 ${m.operator_id}` : '后台',
  }
}

/**
 * 加载各类库存流水（入库 / 盘点 / 报损 / 全部）
 * @returns {Promise<void>}
 */
async function loadMovements() {
  try {
    const [inbound, stocktake, breakage, all] = await Promise.all([
      fetchInventoryMovements({ type: 'inbound', pageSize: 50 }),
      fetchInventoryMovements({ type: 'stocktake', pageSize: 50 }),
      fetchInventoryMovements({ type: 'breakage', pageSize: 50 }),
      fetchInventoryMovements({ pageSize: 50 }),
    ])
    inboundRecords.value = (inbound.items || []).map(toFlowRow)
    stocktakeRecords.value = (stocktake.items || []).map(toFlowRow)
    breakageRecords.value = (breakage.items || []).map(toFlowRow)
    flows.value = (all.items || []).map(toFlowRow)
  } catch (err) {
    ElMessage.error(`库存流水加载失败：${err.message}`)
  }
}

/**
 * 刷新商品、库存与流水
 */
function refreshAll() {
  loadProducts()
  loadInventory()
  loadMovements()
  ElMessage.success('库存已刷新')
}

/* ---------------- 采购入库 ---------------- */

// 入库弹窗显隐
const purchaseDialog = ref(false)
// 入库明细行
const purchaseItems = ref([])

/**
 * 打开入库弹窗：可从库存行带出商品
 * @param {object} [row] 库存行
 */
const openPurchaseDialog = (row) => {
  purchaseItems.value = row
    ? [{ productId: row.product_id, qty: 1, price: Number(row.cost_price || 5) }]
    : []
  purchaseDialog.value = true
}

/**
 * 追加一行入库明细
 */
const addPurchaseRow = () => purchaseItems.value.push({ productId: null, qty: 1, price: 5 })

// 入库合计金额
const purchaseTotal = computed(() => purchaseItems.value.reduce((sum, r) => sum + r.qty * r.price, 0))

/**
 * 提交入库：逐行调用入库接口
 * @returns {Promise<void>}
 */
async function submitPurchase() {
  if (purchaseItems.value.some((r) => !r.productId)) {
    ElMessage.warning('请完整选择入库商品')
    return
  }
  try {
    for (const row of purchaseItems.value) {
      await inventoryInbound({ productId: row.productId, qty: row.qty, costPrice: row.price })
    }
    ElMessage.success('入库完成，库存已更新')
    purchaseDialog.value = false
    refreshAll()
  } catch (err) {
    ElMessage.error(`入库失败：${err.message}`)
  }
}

/* ---------------- 盘点 ---------------- */

// 盘点弹窗显隐
const checkDialog = ref(false)
// 盘点明细行
const checkItems = ref([])

/**
 * 打开盘点弹窗
 */
const openCheckDialog = () => {
  checkItems.value = []
  checkDialog.value = true
}

/**
 * 追加一行盘点明细
 */
const addCheckRow = () => checkItems.value.push({ productId: null, actual: 0 })

/**
 * 提交盘点：逐行按实盘数覆盖库存
 * @returns {Promise<void>}
 */
async function submitCheck() {
  if (checkItems.value.some((r) => !r.productId)) {
    ElMessage.warning('请完整选择盘点商品')
    return
  }
  try {
    for (const row of checkItems.value) {
      await inventoryStocktake({ productId: row.productId, actual: row.actual })
    }
    ElMessage.success('盘点完成，库存已按实盘数更新')
    checkDialog.value = false
    refreshAll()
  } catch (err) {
    ElMessage.error(`盘点失败：${err.message}`)
  }
}

/* ---------------- 报损 ---------------- */

// 报损弹窗显隐
const lossDialog = ref(false)
// 报损表单
const lossForm = reactive({ productId: null, qty: 1, reason: '损耗', note: '' })

/**
 * 打开报损弹窗：可从库存行带出商品
 * @param {object} [row] 库存行
 */
const openLossDialog = (row) => {
  lossForm.productId = row ? row.product_id : null
  lossForm.qty = 1
  lossForm.reason = '损耗'
  lossForm.note = ''
  lossDialog.value = true
}

/**
 * 提交报损登记
 * @returns {Promise<void>}
 */
async function submitLoss() {
  if (!lossForm.productId) {
    ElMessage.warning('请选择报损商品')
    return
  }
  try {
    await inventoryBreakage({ productId: lossForm.productId, qty: lossForm.qty })
    ElMessage.success('报损登记完成，库存已扣减')
    lossDialog.value = false
    refreshAll()
  } catch (err) {
    ElMessage.error(`报损失败：${err.message}`)
  }
}

/* ---------------- 变动流水搜索 ---------------- */

// 流水搜索关键字
const flowKeyword = ref('')

// 按商品 / 来源 / 类型过滤流水
const filteredFlows = computed(() => {
  const k = flowKeyword.value.trim()
  if (!k) return flows.value
  return flows.value.filter((f) => f.product.includes(k) || f.refNo.includes(k) || f.type.includes(k))
})

// 页面挂载：先加载商品（流水单位依赖商品信息），再加载库存与流水
onMounted(async () => {
  await loadProducts()
  loadInventory()
  loadMovements()
})
</script>

<style scoped>
.inventory {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
/* 统一卡片样式 */
.card {
  background: #fff;
  border-radius: var(--radius-md);
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--neutral-200);
}
.tab-bar :deep(.el-tabs__nav-wrap::after) {
  background-color: var(--neutral-200);
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
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.cell-time {
  font-size: 12px;
  color: var(--neutral-400);
}
.text-danger {
  color: var(--danger);
  font-weight: 600;
}
.text-success {
  color: var(--success);
  font-weight: 600;
}
/* 分页容器：右对齐 */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.dialog-tip {
  font-size: 12px;
  color: var(--neutral-500);
  margin-bottom: 12px;
}
.dialog-table {
  margin-bottom: 12px;
}
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.total-hint {
  font-size: 13px;
  color: var(--neutral-600);
}
</style>
