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
            placeholder="搜索商品 / 分类"
            clearable
            :prefix-icon="Search"
            style="width: 240px"
          />
          <el-button type="primary" :icon="Refresh" @click="ElMessage.success('库存已刷新')">刷新库存</el-button>
        </div>
      </div>
      <el-table :data="filteredStocks" v-loading="loading" empty-text="暂无库存数据">
        <el-table-column prop="name" label="商品" min-width="140" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="100" align="center" />
        <el-table-column label="库存" width="110" align="right">
          <template #default="{ row }">
            <span class="num" :class="{ 'text-danger': row.status !== '充足' }">{{ row.stock }}</span>
          </template>
        </el-table-column>
        <el-table-column label="安全库存" width="110" align="right">
          <template #default="{ row }"><span class="num">{{ row.safety }}</span></template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="stockTagType(row.status)" effect="light">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="110" align="right">
          <template #default="{ row }"><span class="cell-time">{{ row.updatedAt }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openPurchaseDialog(row)">入库</el-button>
            <el-button link type="warning" size="small" @click="openLossDialog(row)">报损</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ========== 2. 采购入库 ========== -->
    <div v-show="activeTab === 'purchase'" class="card">
      <div class="card-head">
        <h3>入库单列表</h3>
        <el-button type="primary" :icon="Plus" @click="openPurchaseDialog()">新建入库单</el-button>
      </div>
      <el-table :data="purchaseOrders" empty-text="暂无入库单">
        <el-table-column prop="orderNo" label="单号" width="170" />
        <el-table-column prop="supplier" label="供应商" width="140" />
        <el-table-column label="商品数" width="90" align="center">
          <template #default="{ row }"><span class="num">{{ row.itemCount }}</span></template>
        </el-table-column>
        <el-table-column label="总金额" width="110" align="right">
          <template #default="{ row }"><span class="num">¥{{ row.total.toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column prop="handler" label="经手人" width="90" align="center" />
        <el-table-column label="时间" width="110" align="right">
          <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === '已入库' ? 'success' : 'warning'" effect="light">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ========== 3. 盘点 ========== -->
    <div v-show="activeTab === 'check'" class="card">
      <div class="card-head">
        <h3>盘点记录</h3>
        <el-button type="primary" :icon="Plus" @click="openCheckDialog()">新建盘点单</el-button>
      </div>
      <el-table :data="checkRecords" empty-text="暂无盘点记录">
        <el-table-column prop="orderNo" label="单号" width="170" />
        <el-table-column label="盘点商品数" width="110" align="center">
          <template #default="{ row }"><span class="num">{{ row.itemCount }}</span></template>
        </el-table-column>
        <el-table-column label="差异数量" width="110" align="center">
          <template #default="{ row }">
            <span class="num" :class="row.diff > 0 ? 'text-success' : 'text-danger'">{{ row.diff > 0 ? '+' : '' }}{{ row.diff }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="操作人" width="90" align="center" />
        <el-table-column label="时间" width="110" align="right">
          <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === '已盘点' ? 'success' : 'info'" effect="light">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ========== 4. 报损 ========== -->
    <div v-show="activeTab === 'loss'" class="card">
      <div class="card-head">
        <h3>报损记录</h3>
        <el-button type="primary" :icon="Plus" @click="openLossDialog()">报损登记</el-button>
      </div>
      <el-table :data="lossRecords" empty-text="暂无报损记录">
        <el-table-column prop="orderNo" label="单号" width="170" />
        <el-table-column prop="product" label="商品" min-width="130" />
        <el-table-column label="数量" width="90" align="right">
          <template #default="{ row }"><span class="num text-danger">{{ row.count }}{{ row.unit }}</span></template>
        </el-table-column>
        <el-table-column label="原因" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="lossReasonTag(row.reason)" effect="light">{{ row.reason }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="handler" label="经手人" width="90" align="center" />
        <el-table-column label="时间" width="110" align="right">
          <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === '已报损' ? 'danger' : 'warning'" effect="light">{{ row.status }}</el-tag>
          </template>
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
        <el-table-column label="时间" width="110" align="right">
          <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column prop="product" label="商品" min-width="130" />
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="flowTypeTag(row.type)" effect="light">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="100" align="right">
          <template #default="{ row }">
            <span class="num" :class="row.change > 0 ? 'text-success' : 'text-danger'">
              {{ row.change > 0 ? '+' : '' }}{{ row.change }}{{ row.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="来源单号" width="170" align="center">
          <template #default="{ row }"><span class="cell-time">{{ row.refNo }}</span></template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="140" show-overflow-tooltip />
      </el-table>
    </div>

    <!-- ========== 采购入库弹窗 ========== -->
    <el-dialog v-model="purchaseDialog" title="新建入库单" width="640px" destroy-on-close>
      <div class="dialog-tip">选择商品并填写进货数量与进价，可添加多行商品明细。</div>
      <el-table :data="purchaseItems" empty-text="请添加入库商品" class="dialog-table">
        <el-table-column label="商品" width="170">
          <template #default="{ row }">
            <el-select v-model="row.product" filterable placeholder="选择商品" size="small">
              <el-option v-for="p in productOptions" :key="p.name" :label="p.name" :value="p.name" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.count" :min="0.01" :precision="2" :step="1" size="small" style="width: 120px" />
          </template>
        </el-table-column>
        <el-table-column label="进价(元)" width="150">
          <template #default="{ row }">
            <el-input-number v-model="row.price" :min="0.01" :precision="2" :step="0.1" size="small" style="width: 130px" />
          </template>
        </el-table-column>
        <el-table-column label="小计" width="90" align="right">
          <template #default="{ row }">
            <span class="num">¥{{ (row.count * row.price).toFixed(2) }}</span>
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
        <el-table-column label="商品" width="170">
          <template #default="{ row }">
            <el-select v-model="row.product" filterable placeholder="选择商品" size="small">
              <el-option v-for="p in productOptions" :key="p.name" :label="p.name" :value="p.name" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="账面数" width="120" align="right">
          <template #default="{ row }"><span class="num">{{ row.book }}</span></template>
        </el-table-column>
        <el-table-column label="实盘数" width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.actual" :min="0" :precision="2" :step="1" size="small" style="width: 120px" />
          </template>
        </el-table-column>
        <el-table-column label="差异" width="100" align="right">
          <template #default="{ row }">
            <span class="num" :class="row.actual - row.book === 0 ? '' : row.actual - row.book > 0 ? 'text-success' : 'text-danger'">
              {{ row.actual - row.book > 0 ? '+' : '' }}{{ (row.actual - row.book).toFixed(2) }}
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
          <el-select v-model="lossForm.product" filterable placeholder="选择商品" style="width: 100%">
            <el-option v-for="p in productOptions" :key="p.name" :label="p.name" :value="p.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="lossForm.count" :min="0.01" :precision="2" :step="1" style="width: 200px" />
        </el-form-item>
        <el-form-item label="原因" required>
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
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Search, Refresh } from '@element-plus/icons-vue'

// 当前激活的 tab
const activeTab = ref('query')
const loading = ref(false)

// ---------- 库存查询 ----------
// 模拟数据：库存列表（低库存标红）
const stocks = ref([
  { name: '上海青', category: '蔬菜', stock: 2.4, safety: 10, unit: 'kg', status: '紧缺', updatedAt: '11-05 18:00' },
  { name: '西红柿', category: '蔬菜', stock: 5, safety: 15, unit: 'kg', status: '不足', updatedAt: '11-05 18:00' },
  { name: '黄瓜', category: '蔬菜', stock: 26, safety: 20, unit: 'kg', status: '充足', updatedAt: '11-05 18:00' },
  { name: '土豆', category: '蔬菜', stock: 12, safety: 40, unit: 'kg', status: '不足', updatedAt: '11-05 18:00' },
  { name: '蜜桔', category: '水果', stock: 6.5, safety: 20, unit: 'kg', status: '紧缺', updatedAt: '11-05 18:00' },
  { name: '香蕉', category: '水果', stock: 38, safety: 25, unit: 'kg', status: '充足', updatedAt: '11-05 18:00' },
  { name: '苹果', category: '水果', stock: 55, safety: 30, unit: 'kg', status: '充足', updatedAt: '11-05 18:00' },
  { name: '五花肉', category: '肉类', stock: 3.2, safety: 8, unit: 'kg', status: '紧缺', updatedAt: '11-05 18:00' },
  { name: '前腿肉', category: '肉类', stock: 22, safety: 10, unit: 'kg', status: '充足', updatedAt: '11-05 18:00' },
  { name: '鲜鸡蛋(盒)', category: '蛋奶', stock: 8, safety: 30, unit: '盒', status: '紧缺', updatedAt: '11-05 18:00' },
])

// 库存状态标签：充足绿 / 不足橙 / 紧缺红
const stockTagType = (s) => (s === '充足' ? 'success' : s === '不足' ? 'warning' : 'danger')

// 搜索关键词过滤
const queryKeyword = ref('')
const filteredStocks = computed(() => {
  const k = queryKeyword.value.trim()
  if (!k) return stocks.value
  return stocks.value.filter((s) => s.name.includes(k) || s.category.includes(k))
})

// ---------- 采购入库 ----------
// 模拟数据：入库单列表
const purchaseOrders = ref([
  { orderNo: 'RK20261105-003', supplier: '绿源蔬菜基地', itemCount: 8, total: 1820.5, handler: '王店长', time: '11-05 14:20', status: '已入库' },
  { orderNo: 'RK20261105-002', supplier: '鲜丰果业', itemCount: 5, total: 965.0, handler: '李采购', time: '11-05 10:05', status: '已入库' },
  { orderNo: 'RK20261105-001', supplier: '双汇冷鲜肉', itemCount: 3, total: 1520.0, handler: '李采购', time: '11-05 08:30', status: '已入库' },
  { orderNo: 'RK20261104-007', supplier: '绿源蔬菜基地', itemCount: 10, total: 2100.0, handler: '王店长', time: '11-04 16:45', status: '待入库' },
])

// 入库单弹窗与明细行
const purchaseDialog = ref(false)
const purchaseItems = ref([])

// 商品候选列表（模拟）
const productOptions = [
  { name: '上海青', unit: 'kg' },
  { name: '西红柿', unit: 'kg' },
  { name: '黄瓜', unit: 'kg' },
  { name: '土豆', unit: 'kg' },
  { name: '蜜桔', unit: 'kg' },
  { name: '香蕉', unit: 'kg' },
  { name: '苹果', unit: 'kg' },
  { name: '五花肉', unit: 'kg' },
  { name: '前腿肉', unit: 'kg' },
  { name: '鲜鸡蛋(盒)', unit: '盒' },
]

// 打开入库弹窗：可从库存列表带出商品
const openPurchaseDialog = (row) => {
  purchaseItems.value = row ? [{ product: row.name, count: 1, price: 5 }] : []
  purchaseDialog.value = true
}

// 添加入库行
const addPurchaseRow = () => purchaseItems.value.push({ product: '', count: 1, price: 5 })

// 入库合计金额
const purchaseTotal = computed(() =>
  purchaseItems.value.reduce((sum, r) => sum + r.count * r.price, 0)
)

// 提交入库（校验商品非空后写入列表，示意）
const submitPurchase = () => {
  if (purchaseItems.value.some((r) => !r.product)) {
    ElMessage.warning('请完整选择入库商品')
    return
  }
  purchaseOrders.value.unshift({
    orderNo: `RK20261105-${String(purchaseOrders.value.length + 1).padStart(3, '0')}`,
    supplier: '绿源蔬菜基地',
    itemCount: purchaseItems.value.length,
    total: purchaseTotal.value,
    handler: '王店长',
    time: '11-05 18:30',
    status: '待入库',
  })
  ElMessage.success('入库单已提交')
  purchaseDialog.value = false
}

// ---------- 盘点 ----------
// 模拟数据：盘点记录
const checkRecords = ref([
  { orderNo: 'PD20261105-001', itemCount: 6, diff: -1.2, operator: '王店长', time: '11-05 09:00', status: '已盘点' },
  { orderNo: 'PD20261104-001', itemCount: 4, diff: 2.5, operator: '张收银', time: '11-04 21:00', status: '已盘点' },
  { orderNo: 'PD20261103-001', itemCount: 8, diff: 0, operator: '王店长', time: '11-03 09:00', status: '盘点中' },
])

// 盘点弹窗与明细行
const checkDialog = ref(false)
const checkItems = ref([])

const openCheckDialog = () => {
  checkItems.value = []
  checkDialog.value = true
}
const addCheckRow = () => checkItems.value.push({ product: '', book: 10, actual: 10 })

// 提交盘点
const submitCheck = () => {
  if (checkItems.value.some((r) => !r.product)) {
    ElMessage.warning('请完整选择盘点商品')
    return
  }
  const totalDiff = checkItems.value.reduce((sum, r) => sum + (r.actual - r.book), 0)
  checkRecords.value.unshift({
    orderNo: `PD20261105-00${checkRecords.value.length + 1}`,
    itemCount: checkItems.value.length,
    diff: Number(totalDiff.toFixed(2)),
    operator: '王店长',
    time: '11-05 18:30',
    status: '盘点中',
  })
  ElMessage.success('盘点单已提交')
  checkDialog.value = false
}

// ---------- 报损 ----------
// 模拟数据：报损记录
const lossRecords = ref([
  { orderNo: 'BS20261105-002', product: '上海青', count: 2.3, unit: 'kg', reason: '损耗', handler: '张收银', time: '11-05 16:10', status: '已报损' },
  { orderNo: 'BS20261105-001', product: '鲜鸡蛋(盒)', count: 3, unit: '盒', reason: '损坏', handler: '张收银', time: '11-05 11:22', status: '已报损' },
  { orderNo: 'BS20261104-001', product: '香蕉', count: 5, unit: 'kg', reason: '过期', handler: '王店长', time: '11-04 20:05', status: '待确认' },
])

// 报损原因标签：损耗橙 / 过期红 / 损坏红
const lossReasonTag = (r) => (r === '损耗' ? 'warning' : 'danger')

// 报损弹窗表单
const lossDialog = ref(false)
const lossForm = reactive({ product: '', count: 1, reason: '损耗', note: '' })

const openLossDialog = (row) => {
  lossForm.product = row ? row.name : ''
  lossForm.count = 1
  lossForm.reason = '损耗'
  lossForm.note = ''
  lossDialog.value = true
}

// 确认报损
const submitLoss = () => {
  if (!lossForm.product) {
    ElMessage.warning('请选择报损商品')
    return
  }
  lossRecords.value.unshift({
    orderNo: `BS20261105-00${lossRecords.value.length + 1}`,
    product: lossForm.product,
    count: lossForm.count,
    unit: 'kg',
    reason: lossForm.reason,
    handler: '王店长',
    time: '11-05 18:30',
    status: '待确认',
  })
  ElMessage.success('报损登记已提交')
  lossDialog.value = false
}

// ---------- 变动流水 ----------
// 模拟数据：库存变动流水（入库绿 / 销售蓝 / 盘点橙 / 报损红）
const flows = ref([
  { time: '11-05 18:20', product: '上海青', type: '入库', change: 20, unit: 'kg', refNo: 'RK20261105-003', note: '采购入库' },
  { time: '11-05 17:45', product: '五花肉', type: '销售', change: -0.42, unit: 'kg', refNo: 'SO20261105-0211', note: '称重销售' },
  { time: '11-05 16:10', product: '上海青', type: '报损', change: -2.3, unit: 'kg', refNo: 'BS20261105-002', note: '损耗报损' },
  { time: '11-05 09:00', product: '土豆', type: '盘点', change: -1.2, unit: 'kg', refNo: 'PD20261105-001', note: '盘亏调整' },
  { time: '11-05 08:30', product: '五花肉', type: '入库', change: 15, unit: 'kg', refNo: 'RK20261105-001', note: '采购入库' },
  { time: '11-04 21:00', product: '蜜桔', type: '盘点', change: 2.5, unit: 'kg', refNo: 'PD20261104-001', note: '盘盈调整' },
  { time: '11-04 19:30', product: '蜜桔', type: '销售', change: -1.6, unit: 'kg', refNo: 'SO20261104-0198', note: '称重销售' },
  { time: '11-04 20:05', product: '香蕉', type: '报损', change: -5, unit: 'kg', refNo: 'BS20261104-001', note: '过期报损' },
])

// 变动类型标签：入库绿 / 销售蓝 / 盘点橙 / 报损红
const flowTypeTag = (t) => (t === '入库' ? 'success' : t === '销售' ? 'primary' : t === '盘点' ? 'warning' : 'danger')

// 流水搜索过滤
const flowKeyword = ref('')
const filteredFlows = computed(() => {
  const k = flowKeyword.value.trim()
  if (!k) return flows.value
  return flows.value.filter((f) => f.product.includes(k) || f.refNo.includes(k) || f.type.includes(k))
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
