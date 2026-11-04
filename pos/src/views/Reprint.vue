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
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Printer, Search, PriceTag } from '@element-plus/icons-vue'

const activeTab = ref('receipt') // 当前 tab

// 订单列表（模拟数据；item.weight 存在表示为称重商品）
const receipts = [
  {
    orderNo: 'XS20261105-0001',
    time: '2026-11-05 09:32',
    mobile: '13800001234',
    amount: 87.14,
    items: [
      { name: '上海青', weight: '0.62', price: 4.8, amount: 2.98 },
      { name: '五花肉', weight: '1.35', price: 28.8, amount: 38.88 },
      { name: '红富士苹果', weight: '1.10', price: 9.8, amount: 10.78 },
      { name: '鲜鸡蛋(盒)', qty: 2, price: 13.8, amount: 27.6 },
      { name: '挂面(袋)', qty: 1, price: 6.9, amount: 6.9 },
    ],
  },
  {
    orderNo: 'XS20261105-0002',
    time: '2026-11-05 10:15',
    mobile: '13900005678',
    amount: 36.31,
    items: [
      { name: '草鱼', weight: '1.20', price: 15.8, amount: 18.96 },
      { name: '黄瓜', weight: '0.85', price: 5.2, amount: 4.42 },
      { name: '土豆', weight: '2.10', price: 3.8, amount: 7.98 },
      { name: '东北大米', weight: '0.90', price: 5.5, amount: 4.95 },
    ],
  },
  {
    orderNo: 'XS20261105-0003',
    time: '2026-11-05 11:02',
    mobile: '13700001122',
    amount: 47.96,
    items: [
      { name: '基围虾', weight: '0.50', price: 42.0, amount: 21.0 },
      { name: '鸡胸肉', weight: '0.80', price: 21.5, amount: 17.2 },
      { name: '西红柿', weight: '0.65', price: 6.5, amount: 4.23 },
      { name: '蜜桔', weight: '0.70', price: 7.9, amount: 5.53 },
    ],
  },
  {
    orderNo: 'XS20261105-0004',
    time: '2026-11-05 14:28',
    mobile: '13600009900',
    amount: 93.26,
    items: [
      { name: '金龙鱼花生油', qty: 1, price: 89.9, amount: 89.9 },
      { name: '香蕉', weight: '0.60', price: 5.6, amount: 3.36 },
    ],
  },
  {
    orderNo: 'XS20261105-0005',
    time: '2026-11-05 15:02',
    mobile: '13500007788',
    amount: 48.3,
    items: [
      { name: '鲜鸡蛋(盒)', qty: 2, price: 13.8, amount: 27.6 },
      { name: '挂面(袋)', qty: 3, price: 6.9, amount: 20.7 },
    ],
  },
]

// 补打小票查询条件
const receiptKeyword = ref('')
const receiptDate = ref('')

// 小票过滤：按订单号 / 手机号 / 日期
const filteredReceipts = computed(() =>
  receipts.filter((o) => {
    const kw = receiptKeyword.value.trim().toLowerCase()
    const inKw = !kw || o.orderNo.toLowerCase().includes(kw) || o.mobile.includes(kw)
    const inDate = !receiptDate.value || o.time.startsWith(receiptDate.value)
    return inKw && inDate
  }),
)

// 点击查询（过滤由 computed 自动完成，此处仅做提示）
const searchReceipt = () => {
  ElMessage.info('已按条件查询（演示）')
}

// 补打价格标签：仅含称重商品的订单
const labelOrders = computed(() =>
  receipts.filter((o) => o.items.some((i) => i.weight)),
)

const labelOrderNo = ref('') // 选中的标签订单号

// 当前选中订单
const currentLabelOrder = computed(() =>
  labelOrders.value.find((o) => o.orderNo === labelOrderNo.value),
)

// 补打小票（示意）
const reprintReceipt = (row) => {
  ElMessage.success(`补打小票成功：${row.orderNo}（示意）`)
}

// 补打单个价格标签（示意）
const reprintLabel = (item) => {
  ElMessage.success(`已补打标签：${item.name}（示意）`)
}

// 补打全部价格标签（示意）
const reprintLabelAll = () => {
  ElMessage.success(`已补打 ${currentLabelOrder.value.items.length} 张价格标签（示意）`)
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
