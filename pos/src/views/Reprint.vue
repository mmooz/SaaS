<template>
  <div class="page">
    <!-- 顶部深色栏 -->
    <header class="page-header">
      <div class="header-title">补打</div>
      <el-button class="back-btn" @click="$router.push('/')"><el-icon><ArrowLeft /></el-icon>&nbsp;返回收银台</el-button>
    </header>

    <div class="page-body">
      <el-tabs v-model="activeTab" class="main-tabs">
        <!-- Tab：补打小票 -->
        <el-tab-pane label="补打小票" name="receipt">
          <!-- 查询条件：订单号 / 手机号 + 日期 -->
          <div class="toolbar">
            <el-input
              v-model="receiptKeyword"
              size="large"
              placeholder="订单号 / 手机号"
              clearable
              class="toolbar-input"
              @keyup.enter="searchReceipt"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-date-picker
              v-model="receiptDate"
              type="date"
              size="large"
              placeholder="选择日期"
              class="toolbar-input"
              value-format="YYYY-MM-DD"
            />
            <el-button type="primary" class="big-btn" @click="searchReceipt">查 询</el-button>
          </div>

          <!-- 订单列表 -->
          <el-table :data="filteredReceipts" class="receipt-table">
            <el-table-column prop="orderNo" label="订单号" min-width="180" />
            <el-table-column prop="time" label="时间" min-width="150" />
            <el-table-column label="金额" min-width="120">
              <template #default="{ row }"><span class="num">¥{{ row.amount.toFixed(2) }}</span></template>
            </el-table-column>
            <el-table-column label="操作" min-width="160">
              <template #default="{ row }">
                <el-button type="primary" class="big-btn table-btn" @click="reprintReceipt(row)">
                  <el-icon><Printer /></el-icon>&nbsp;补打小票
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Tab：补打价格标签 -->
        <el-tab-pane label="补打价格标签" name="label">
          <!-- 选择含称重商品的订单 -->
          <div class="toolbar">
            <el-select v-model="labelOrderNo" size="large" placeholder="选择含称重商品的订单" class="toolbar-input">
              <el-option v-for="o in labelOrders" :key="o.orderNo" :label="`${o.orderNo} · ${o.time}`" :value="o.orderNo" />
            </el-select>
            <el-button class="big-btn" :disabled="!currentLabelOrder" @click="reprintLabelAll">补打全部标签</el-button>
          </div>

          <!-- 选中订单的称重商品列表 -->
          <section v-if="currentLabelOrder" class="label-card">
            <div class="label-head">
              <div class="order-no">{{ currentLabelOrder.orderNo }}</div>
              <div class="order-meta">{{ currentLabelOrder.time }} · {{ currentLabelOrder.items.length }} 个称重商品</div>
            </div>
            <div v-for="item in currentLabelOrder.items" :key="item.name" class="label-row">
              <div class="label-info">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-sub num">{{ item.weight }}kg × ¥{{ item.price.toFixed(2) }}</div>
              </div>
              <div class="item-amount num">¥{{ item.amount.toFixed(2) }}</div>
              <el-button type="primary" class="big-btn table-btn" @click="reprintLabel(item)">
                <el-icon><PriceTag /></el-icon>&nbsp;补打标签
              </el-button>
            </div>
          </section>
          <div v-else class="empty-tip">请选择需要补打标签的订单</div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Printer, Search, PriceTag } from '@element-plus/icons-vue'
import { fetchOrderByNo, fetchOrders } from '../api'
import { PrintService } from '../services/print/PrintService'
import { OrderPrintMapper } from '../services/print/OrderPrintMapper'
import { PrintFormatter as F } from '../services/print/PrintFormatter'

const activeTab = ref('receipt') // 当前 tab
const loading = ref(false)

// 订单列表（来自服务端）
const receipts = ref([])

/**
 * 服务端订单转页面展示模型
 * @param {object} order 服务端订单（OrderOut）
 * @returns {object} 展示模型
 */
function toDisplay(order) {
  return {
    orderNo: order.order_no,
    time: F.datetime(order.created_at),
    mobile: order.member_id ? `会员#${order.member_id}` : '',
    amount: order.total_amount,
    payMethod: OrderPrintMapper.payMethod(order.pay_details),
    items: (order.items || []).map((item) => ({
      productId: item.product_id,
      name: item.name,
      weighted: !!item.is_weighted,
      weight: item.is_weighted ? Number(item.weight_kg || 0).toFixed(2) : '',
      qty: item.qty,
      price: item.unit_price,
      amount: item.amount,
    })),
    printModel: OrderPrintMapper.fromServer(order),
  }
}

/**
 * 加载最近的订单列表
 * @returns {Promise<void>}
 */
async function loadOrders() {
  loading.value = true
  try {
    const data = await fetchOrders({ page: 1, pageSize: 20 })
    receipts.value = (data.items || []).map(toDisplay)
  } catch (err) {
    ElMessage.error(`订单加载失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

onMounted(loadOrders)

// 补打小票查询条件
const receiptKeyword = ref('')
const receiptDate = ref('')

// 小票过滤：按订单号 / 会员 / 日期
const filteredReceipts = computed(() =>
  receipts.value.filter((o) => {
    const kw = receiptKeyword.value.trim().toLowerCase()
    const inKw = !kw || o.orderNo.toLowerCase().includes(kw) || o.mobile.includes(kw)
    const inDate = !receiptDate.value || o.time.startsWith(receiptDate.value)
    return inKw && inDate
  }),
)

// 查询：关键字像订单号时精确查询，否则重新拉取列表
const searchReceipt = async () => {
  const kw = receiptKeyword.value.trim()
  if (kw && /\d{4}-\d{5}$/.test(kw) === false && /\d$/.test(kw) && kw.length >= 8) {
    try {
      const order = await fetchOrderByNo(kw)
      receipts.value = [toDisplay(order), ...receipts.value.filter((o) => o.orderNo !== order.order_no)]
      ElMessage.success('已定位订单')
      return
    } catch {
      // 精确查询失败则退回列表查询
    }
  }
  await loadOrders()
  ElMessage.info(`已查询 ${receipts.value.length} 笔订单`)
}

// 补打价格标签：仅含称重商品的订单
const labelOrders = computed(() =>
  receipts.value.filter((o) => o.items.some((i) => i.weighted)),
)

const labelOrderNo = ref('') // 选中的标签订单号

// 当前选中订单
const currentLabelOrder = computed(() =>
  labelOrders.value.find((o) => o.orderNo === labelOrderNo.value),
)

// 补打小票：调用打印通道重新出票
const reprintReceipt = async (row) => {
  const channel = await PrintService.printReceipt(row.printModel)
  if (channel === 'failed') {
    ElMessage.error('补打失败：所选小票打印机不存在，请到设置页重新选择')
    return
  }
  ElMessage.success(`已补打小票：${row.orderNo}`)
}

// 补打单个价格标签
const reprintLabel = async (item) => {
  const channel = await PrintService.printLabel(currentLabelOrder.value.printModel, item)
  if (channel === 'failed') {
    ElMessage.error('补打失败：所选标签打印机不存在，请到设置页重新选择')
    return
  }
  ElMessage.success(`已补打标签：${item.name}`)
}

// 补打全部价格标签
const reprintLabelAll = async () => {
  const count = await PrintService.printLabels(
    currentLabelOrder.value.printModel,
    currentLabelOrder.value.printModel.items,
  )
  if (count < 0) {
    ElMessage.error('补打失败：所选标签打印机不存在，请到设置页重新选择')
    return
  }
  ElMessage.success(`已补打 ${count} 张价格标签`)
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--neutral-100);
}

/* ----- 顶部深色栏（与 PosMain 呼应） ----- */
.page-header {
  height: 64px;
  background: var(--neutral-900);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}
.header-title {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 1px;
}
.page-header :deep(.el-button) {
  height: 44px;
  border-radius: var(--radius-md);
  background: oklch(30% 0.02 152);
  border-color: oklch(45% 0.02 152);
  color: #fff;
  font-size: 16px;
}
.page-header :deep(.el-button:hover) {
  background: oklch(40% 0.03 152);
  color: #fff;
}

/* ----- 页面主体 ----- */
.page-body {
  flex: 1;
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  padding: var(--space-5) var(--space-4);
}

/* 触屏大按钮统一样式 */
.big-btn {
  height: 48px;
  font-size: 17px;
  border-radius: var(--radius-md);
  padding: 0 28px;
}

/* ----- 顶部 Tab ----- */
.main-tabs :deep(.el-tabs__item) {
  font-size: 17px;
  font-weight: 600;
  height: 52px;
  padding: 0 24px;
}
.main-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 2px;
}

/* ----- 查询工具栏 ----- */
.toolbar {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-top: var(--space-2);
}
.toolbar-input {
  width: 260px;
}
.toolbar-input :deep(.el-input__wrapper) {
  min-height: 48px;
  border-radius: var(--radius-md);
}
.toolbar-input :deep(.el-input__inner),
.toolbar-input :deep(.el-select__placeholder) {
  font-size: 16px;
}

/* ----- 小票表格 ----- */
.receipt-table {
  margin-top: var(--space-3);
}
.receipt-table :deep(.el-table__row) {
  font-size: 15px;
}
.receipt-table :deep(th.el-table__cell) {
  font-size: 15px;
  background: var(--neutral-50);
  color: var(--neutral-600);
}
.table-btn {
  height: 44px;
  font-size: 15px;
  padding: 0 18px;
}

/* ----- 标签列表 ----- */
.label-card {
  margin-top: var(--space-3);
  background: #fff;
  border-radius: var(--radius-lg);
  border: 1px solid var(--neutral-200);
  box-shadow: var(--shadow-sm);
  padding: var(--space-4);
}
.label-head {
  margin-bottom: var(--space-3);
}
.order-no {
  font-size: 17px;
  font-weight: 700;
  color: var(--neutral-900);
}
.order-meta {
  font-size: 13px;
  color: var(--neutral-400);
  margin-top: 4px;
}
.label-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 13px 14px;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  margin-bottom: 10px;
}
.label-info {
  flex: 1;
}
.item-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-900);
}
.item-sub {
  font-size: 13px;
  color: var(--neutral-400);
  margin-top: 4px;
}
.item-amount {
  width: 100px;
  text-align: right;
  font-size: 18px;
  font-weight: 700;
  color: var(--danger);
}

/* ----- 空提示 ----- */
.empty-tip {
  text-align: center;
  padding: var(--space-5) 0;
  color: var(--neutral-400);
  font-size: 15px;
}
</style>
