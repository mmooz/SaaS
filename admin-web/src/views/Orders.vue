<!-- 订单与退款管理页面：订单检索、详情查看、退款操作与退款记录 -->
<template>
  <div class="order-page">
    <!-- 筛选工具栏 -->
    <div class="filters">
      <el-input
        v-model="filters.keyword"
        placeholder="订单号 / 会员手机号"
        clearable
        class="filter-keyword"
        @keyup.enter="search"
      />
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        class="filter-date"
      />
      <el-select v-model="filters.status" placeholder="订单状态" clearable class="filter-status">
        <el-option label="已支付" value="paid" />
        <el-option label="部分退款" value="partially_refunded" />
        <el-option label="已退款" value="refunded" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
    </div>

    <!-- 订单列表 -->
    <el-table :data="orders" v-loading="loading" stripe empty-text="暂无订单数据">
      <el-table-column prop="order_no" label="订单号" min-width="190" />
      <el-table-column label="下单时间" min-width="160">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="会员手机号" min-width="130">
        <template #default="{ row }">{{ row.member_mobile || '-' }}</template>
      </el-table-column>
      <el-table-column label="应收金额" width="110" align="right">
        <template #default="{ row }">￥{{ money(row.total_amount) }}</template>
      </el-table-column>
      <el-table-column label="已退款" width="110" align="right">
        <template #default="{ row }">
          <span :class="{ 'text-danger': row.refunded_amount > 0 }">￥{{ money(row.refunded_amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="支付方式" min-width="110">
        <template #default="{ row }">{{ payMethods(row.pay_details) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusMeta(row.status).type" effect="light">
            {{ statusMeta(row.status).label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button
            link
            type="warning"
            :disabled="row.status === 'refunded'"
            @click="openRefund(row)"
          >
            退款
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadOrders"
        @size-change="search"
      />
    </div>

    <!-- 订单详情抽屉 -->
    <el-drawer v-model="detailVisible" title="订单详情" size="640px" destroy-on-close>
      <div v-if="detail" class="detail-body">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="订单号">{{ detail.order_no }}</el-descriptions-item>
          <el-descriptions-item label="下单时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="会员手机号">{{ detail.member_mobile || '-' }}</el-descriptions-item>
          <el-descriptions-item label="订单状态">
            <el-tag :type="statusMeta(detail.status).type" effect="light">
              {{ statusMeta(detail.status).label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="应收金额">￥{{ money(detail.total_amount) }}</el-descriptions-item>
          <el-descriptions-item label="已退款金额">￥{{ money(detail.refunded_amount) }}</el-descriptions-item>
          <el-descriptions-item label="优惠金额">￥{{ money(detail.discount_amount) }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ detail.remark || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>支付明细</h4>
          <div v-if="payDetails.length" class="pay-tags">
            <el-tag v-for="item in payDetails" :key="item.name" effect="plain">
              {{ item.name }} ￥{{ money(item.amount) }}
            </el-tag>
          </div>
          <el-empty v-else description="暂无支付明细" :image-size="60" />
        </div>

        <div class="detail-section">
          <h4>商品明细</h4>
          <el-table :data="detail.items" size="small" border empty-text="暂无商品明细">
            <el-table-column prop="name" label="商品" min-width="130" />
            <el-table-column label="数量/重量" width="110">
              <template #default="{ row }">
                {{ row.is_weighted ? `${row.weight_kg || 0} kg` : `${row.qty} 件` }}
              </template>
            </el-table-column>
            <el-table-column label="单价" width="90" align="right">
              <template #default="{ row }">￥{{ money(row.unit_price) }}</template>
            </el-table-column>
            <el-table-column label="金额" width="90" align="right">
              <template #default="{ row }">￥{{ money(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.refunded" type="info" size="small">已退</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="detail-section">
          <h4>退款记录</h4>
          <el-table :data="refundRecords" size="small" border empty-text="暂无退款记录">
            <el-table-column prop="refund_no" label="退款单号" min-width="150" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">{{ row.refund_type === 'full' ? '整单' : '单项' }}</template>
            </el-table-column>
            <el-table-column label="金额" width="90" align="right">
              <template #default="{ row }">￥{{ money(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="原因" min-width="110">
              <template #default="{ row }">{{ row.reason || '-' }}</template>
            </el-table-column>
            <el-table-column label="退款时间" min-width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <div v-else v-loading="detailLoading" class="detail-loading" />
    </el-drawer>

    <!-- 退款弹窗 -->
    <el-dialog v-model="refundVisible" title="订单退款" width="620px" destroy-on-close>
      <div v-if="refundOrderData">
        <el-alert
          :title="`订单 ${refundOrderData.order_no}，可退金额 ￥${money(remainingAmount)}`"
          type="info"
          :closable="false"
          class="refund-alert"
        />
        <el-radio-group v-model="refundType" class="refund-type">
          <el-radio value="full">整单退款</el-radio>
          <el-radio value="item">按商品退货</el-radio>
        </el-radio-group>

        <el-table
          v-if="refundType === 'item'"
          :data="refundOrderData.items"
          size="small"
          border
          @selection-change="onSelectionChange"
        >
          <el-table-column type="selection" width="46" :selectable="isSelectable" />
          <el-table-column prop="name" label="商品" min-width="140" />
          <el-table-column label="数量/重量" width="110">
            <template #default="{ row }">
              {{ row.is_weighted ? `${row.weight_kg || 0} kg` : `${row.qty} 件` }}
            </template>
          </el-table-column>
          <el-table-column label="金额" width="90" align="right">
            <template #default="{ row }">￥{{ money(row.amount) }}</template>
          </el-table-column>
          <el-table-column label="退货状态" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.refunded" type="info" size="small">已退</el-tag>
              <span v-else>可退</span>
            </template>
          </el-table-column>
        </el-table>

        <el-form label-width="80px" class="refund-form">
          <el-form-item label="退款原因">
            <el-input v-model="refundReason" type="textarea" :rows="2" maxlength="200" show-word-limit />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="refundVisible = false">取消</el-button>
        <el-button type="warning" :loading="refunding" @click="submitRefund">确认退款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import {
  fetchOrderDetail,
  fetchOrderRefunds,
  fetchOrders,
  refundOrder,
} from '../api'

// 订单列表数据
const orders = ref([])
// 列表加载状态
const loading = ref(false)
// 总记录数
const total = ref(0)
// 当前页码
const page = ref(1)
// 每页条数
const pageSize = ref(20)

// 筛选条件
const filters = reactive({
  keyword: '',
  dateRange: [],
  status: '',
})

// 订单详情抽屉可见状态
const detailVisible = ref(false)
// 当前订单详情
const detail = ref(null)
// 详情加载状态
const detailLoading = ref(false)
// 当前订单的退款记录
const refundRecords = ref([])

// 退款弹窗可见状态
const refundVisible = ref(false)
// 正在退款的订单数据
const refundOrderData = ref(null)
// 退款类型：full=整单退款，item=按商品退货
const refundType = ref('full')
// 选中的退货明细 ID
const selectedItemIds = ref([])
// 退款原因
const refundReason = ref('')
// 退款提交状态
const refunding = ref(false)

// 可退金额（应收减去已退）
const remainingAmount = computed(() => {
  if (!refundOrderData.value) return 0
  const remaining = refundOrderData.value.total_amount - (refundOrderData.value.refunded_amount || 0)
  return remaining > 0 ? remaining : 0
})

// 支付明细解析结果（形如 [{ name, amount }]）
const payDetails = computed(() => {
  if (!detail.value || !detail.value.pay_details) return []
  try {
    const parsed = JSON.parse(detail.value.pay_details)
    return Object.keys(parsed).map((name) => ({ name, amount: Number(parsed[name]) || 0 }))
  } catch {
    return []
  }
})

/**
 * 把接口时间转成便于阅读的本地时间
 * @param {string} value ISO 时间字符串
 * @returns {string} 格式化时间
 */
function formatTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

/**
 * 金额格式化（保留两位小数）
 * @param {number} value 金额
 * @returns {string} 金额文本
 */
function money(value) {
  return Number(value || 0).toFixed(2)
}

/**
 * 订单状态展示文案与标签色
 * @param {string} status 订单状态
 * @returns {{ label: string, type: string }} 展示信息
 */
function statusMeta(status) {
  const map = {
    paid: { label: '已支付', type: 'success' },
    partially_refunded: { label: '部分退款', type: 'warning' },
    refunded: { label: '已退款', type: 'info' },
  }
  return map[status] || { label: status || '-', type: 'info' }
}

/**
 * 解析支付方式名称列表
 * @param {string} payDetails 支付明细 JSON
 * @returns {string} 支付方式文本
 */
function payMethods(payDetails) {
  try {
    const keys = Object.keys(JSON.parse(payDetails || '{}'))
    return keys.length ? keys.join(' / ') : '-'
  } catch {
    return '-'
  }
}

/**
 * 组装时间范围参数：结束日期按当天 23:59:59 处理
 * @returns {{ start?: string, end?: string }} 时间参数
 */
function timeParams() {
  const [start, end] = filters.dateRange || []
  return {
    start: start ? `${start} 00:00:00` : undefined,
    end: end ? `${end} 23:59:59` : undefined,
  }
}

/**
 * 加载订单列表
 * @returns {Promise<void>}
 */
async function loadOrders() {
  loading.value = true
  try {
    const res = await fetchOrders({
      keyword: filters.keyword.trim() || undefined,
      status: filters.status || undefined,
      page: page.value,
      pageSize: pageSize.value,
      ...timeParams(),
    })
    orders.value = res.items || []
    total.value = res.total || 0
  } catch (err) {
    ElMessage.error(`加载订单失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

/**
 * 按当前筛选条件重新查询（回到第一页）
 * @returns {Promise<void>}
 */
async function search() {
  page.value = 1
  await loadOrders()
}

/**
 * 重置筛选条件并重新查询
 * @returns {Promise<void>}
 */
async function resetFilters() {
  filters.keyword = ''
  filters.dateRange = []
  filters.status = ''
  await search()
}

/**
 * 打开订单详情抽屉
 * @param {object} row 订单行数据
 * @returns {Promise<void>}
 */
async function openDetail(row) {
  detailVisible.value = true
  detail.value = null
  refundRecords.value = []
  detailLoading.value = true
  try {
    const [full, records] = await Promise.all([
      fetchOrderDetail(row.order_no),
      fetchOrderRefunds(row.order_no),
    ])
    detail.value = full
    refundRecords.value = records || []
  } catch (err) {
    ElMessage.error(`加载订单详情失败：${err.message}`)
  } finally {
    detailLoading.value = false
  }
}

/**
 * 打开退款弹窗（先拉取最新订单，避免使用列表中的过期退货状态）
 * @param {object} row 订单行数据
 * @returns {Promise<void>}
 */
async function openRefund(row) {
  try {
    const full = await fetchOrderDetail(row.order_no)
    refundOrderData.value = full
    refundType.value = 'full'
    selectedItemIds.value = []
    refundReason.value = ''
    refundVisible.value = true
  } catch (err) {
    ElMessage.error(`加载订单信息失败：${err.message}`)
  }
}

/**
 * 判断明细行是否可勾选退货
 * @param {object} row 明细行
 * @returns {boolean} 未退过货返回 true
 */
function isSelectable(row) {
  return !row.refunded
}

/**
 * 记录勾选的退货明细
 * @param {Array<object>} rows 选中行
 * @returns {void}
 */
function onSelectionChange(rows) {
  selectedItemIds.value = rows.map((row) => row.id)
}

/**
 * 提交退款
 * @returns {Promise<void>}
 */
async function submitRefund() {
  if (!refundOrderData.value) return
  if (refundType.value === 'item' && !selectedItemIds.value.length) {
    ElMessage.warning('请选择要退货的商品')
    return
  }
  try {
    await ElMessageBox.confirm(
      refundType.value === 'full'
        ? `将整单退款 ￥${money(remainingAmount.value)}，是否继续？`
        : `将退还选中商品，是否继续？`,
      '退款确认',
      { type: 'warning', confirmButtonText: '确认退款', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  refunding.value = true
  try {
    await refundOrder(
      refundOrderData.value.order_no,
      refundType.value === 'full'
        ? { refund_type: 'full', reason: refundReason.value || null }
        : {
            refund_type: 'item',
            item_ids: selectedItemIds.value,
            reason: refundReason.value || null,
          },
    )
    ElMessage.success('退款已完成')
    refundVisible.value = false
    await loadOrders()
    // 若详情抽屉正打开，同步刷新详情与退款记录
    if (detailVisible.value && detail.value) {
      await openDetail({ order_no: detail.value.order_no })
    }
  } catch (err) {
    ElMessage.error(`退款失败：${err.message}`)
  } finally {
    refunding.value = false
  }
}

onMounted(loadOrders)
</script>

<style scoped>
.order-page {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  box-shadow: var(--shadow-sm);
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}
.filter-keyword {
  width: 220px;
}
.filter-date {
  width: 260px;
}
.filter-status {
  width: 140px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.detail-body {
  padding: 0 4px;
}
.detail-section {
  margin-top: 18px;
}
.detail-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--neutral-700);
}
.detail-loading {
  height: 200px;
}
.pay-tags {
  display: flex;
  gap: 8px;
}
.refund-alert {
  margin-bottom: 12px;
}
.refund-type {
  margin-bottom: 12px;
}
.refund-form {
  margin-top: 12px;
}
.text-danger {
  color: var(--danger, #d93838);
}
</style>
