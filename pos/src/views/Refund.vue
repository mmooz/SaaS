<template>
  <div class="page">
    <!-- 顶部深色栏 -->
    <header class="page-header">
      <div class="header-title">退款退货</div>
      <el-button class="back-btn" @click="$router.push('/')"><el-icon><ArrowLeft /></el-icon>&nbsp;返回收银台</el-button>
    </header>

    <div class="page-body">
      <!-- 搜索区：按订单号 / 手机号查询 -->
      <div class="search-bar">
        <el-input
          v-model="keyword"
          size="large"
          placeholder="输入订单号 / 手机号"
          clearable
          class="search-input"
          @keyup.enter="doSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" class="big-btn search-btn" @click="doSearch">搜 索</el-button>
      </div>

      <!-- 无结果提示 -->
      <div v-if="showEmptyTip" class="empty-tip">未找到相关订单，请核对单号或手机号</div>

      <!-- 订单结果卡 -->
      <section v-for="o in resultOrders" :key="o.orderNo" class="order-card">
        <div class="order-head">
          <div>
            <div class="order-no">{{ o.orderNo }}</div>
            <div class="order-meta">{{ o.time }} · {{ o.payMethod }} · {{ o.cashier }}</div>
          </div>
          <div class="order-amount num">¥{{ o.amount.toFixed(2) }}</div>
        </div>

        <!-- 商品明细列表：勾选商品后可用于单项退货 -->
        <div class="item-list">
          <label
            v-for="item in o.items"
            :key="item.name"
            class="item-row"
            :class="{ checked: isChecked(o, item) }"
          >
            <input type="checkbox" :checked="isChecked(o, item)" @change="toggleItem(o, item)" />
            <span class="item-name">{{ item.name }}</span>
            <span class="item-sub num">{{ item.weight ? `${item.weight}kg × ¥${item.price.toFixed(2)}` : `× ${item.qty}` }}</span>
            <span class="item-amount num">¥{{ item.amount.toFixed(2) }}</span>
          </label>
        </div>

        <!-- 权限提示：非本人当班订单需要店长授权 -->
        <div v-if="!o.isSelf" class="auth-tip">
          <el-icon><WarningFilled /></el-icon>&nbsp;该订单非本人当班，需要店长授权
        </div>

        <div class="order-ops">
          <el-button type="danger" class="big-btn" @click="openRefund(o, 'full')">整单退款</el-button>
          <el-button class="big-btn" :disabled="!hasChecked(o)" @click="openRefund(o, 'item')">单项退货</el-button>
        </div>
      </section>
    </div>

    <!-- 退款确认弹窗 -->
    <el-dialog v-model="refundDialog" :title="refundType === 'full' ? '整单退款' : '单项退货'" width="420px">
      <div class="refund-dialog">
        <div class="refund-label">退款金额</div>
        <div class="refund-amount num">¥{{ refundAmount.toFixed(2) }}</div>
        <div class="refund-meta">原支付方式：{{ currentOrder?.payMethod }} · 退款将原路退回</div>
      </div>
      <template #footer>
        <el-button class="big-btn" @click="refundDialog = false">取 消</el-button>
        <el-button type="danger" class="big-btn" @click="confirmRefund">确认退款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Search, WarningFilled } from '@element-plus/icons-vue'

// 模拟订单数据（item.weight 存在表示称重商品）
const orders = [
  {
    orderNo: 'XS20261105-0001',
    time: '2026-11-05 09:32',
    mobile: '13800001234',
    payMethod: '微信',
    cashier: '收银员 小李',
    isSelf: true,
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
    payMethod: '现金',
    cashier: '收银员 小王',
    isSelf: false,
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
    payMethod: '储值',
    cashier: '收银员 小李',
    isSelf: true,
    amount: 47.96,
    items: [
      { name: '基围虾', weight: '0.50', price: 42.0, amount: 21.0 },
      { name: '鸡胸肉', weight: '0.80', price: 21.5, amount: 17.2 },
      { name: '西红柿', weight: '0.65', price: 6.5, amount: 4.23 },
      { name: '蜜桔', weight: '0.70', price: 7.9, amount: 5.53 },
    ],
  },
]

const keyword = ref('')

// 搜索结果：按订单号或手机号过滤，留空显示全部订单
const resultOrders = computed(() =>
  orders.filter((o) => {
    const kw = keyword.value.trim().toLowerCase()
    return !kw || o.orderNo.toLowerCase().includes(kw) || o.mobile.includes(kw)
  }),
)

// 无结果提示：仅在输入了关键字且无匹配时显示
const showEmptyTip = computed(
  () => resultOrders.value.length === 0 && keyword.value.trim() !== '',
)

// 点击搜索（过滤由 computed 自动完成，此处仅做提示）
const doSearch = () => {
  if (!keyword.value.trim()) ElMessage.info('留空查询将显示全部订单')
}

// 勾选集合：`${订单号}::${商品名}` -> 是否勾选（用于单项退货）
const checkedMap = ref({})

const isChecked = (o, item) => checkedMap.value[`${o.orderNo}::${item.name}`] === true

// 切换商品勾选状态
const toggleItem = (o, item) => {
  const key = `${o.orderNo}::${item.name}`
  checkedMap.value[key] = !checkedMap.value[key]
}

// 当前订单是否存在勾选商品（单项退货按钮可用性）
const hasChecked = (o) => o.items.some((i) => isChecked(o, i))

// 退款弹窗状态
const refundDialog = ref(false)
const refundType = ref('full') // full=整单退款 item=单项退货
const currentOrder = ref(null)
const refundAmount = ref(0)

// 打开退款确认弹窗：整单退全部金额，单项退勾选商品合计
const openRefund = (o, type) => {
  currentOrder.value = o
  refundType.value = type
  if (type === 'full') {
    refundAmount.value = o.amount
  } else {
    refundAmount.value = o.items.reduce((s, i) => (isChecked(o, i) ? s + i.amount : s), 0)
  }
  refundDialog.value = true
}

// 确认退款：演示成功提示
const confirmRefund = () => {
  refundDialog.value = false
  ElMessage.success('退款成功，已原路退回')
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
  max-width: 860px;
  margin: 0 auto;
  padding: var(--space-5) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* 触屏大按钮统一样式 */
.big-btn {
  height: 48px;
  font-size: 17px;
  border-radius: var(--radius-md);
  padding: 0 28px;
}

/* ----- 搜索区 ----- */
.search-bar {
  display: flex;
  gap: var(--space-3);
}
.search-input {
  flex: 1;
}
.search-input :deep(.el-input__wrapper) {
  min-height: 50px;
  border-radius: var(--radius-md);
}
.search-input :deep(.el-input__inner) {
  font-size: 17px;
}
.search-btn {
  height: 50px;
  min-width: 120px;
  font-size: 18px;
  letter-spacing: 2px;
}

/* ----- 无结果提示 ----- */
.empty-tip {
  text-align: center;
  padding: var(--space-5) 0;
  color: var(--neutral-400);
  font-size: 15px;
}

/* ----- 订单结果卡 ----- */
.order-card {
  background: #fff;
  border-radius: var(--radius-lg);
  border: 1px solid var(--neutral-200);
  box-shadow: var(--shadow-sm);
  padding: var(--space-4);
}
.order-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
.order-amount {
  font-size: 24px;
  font-weight: 700;
  color: var(--danger);
}

/* ----- 商品明细（可勾选） ----- */
.item-list {
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: var(--space-3);
}
.item-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 14px;
  border-bottom: 1px solid var(--neutral-100);
  cursor: pointer;
  font-size: 15px;
}
.item-row:last-child {
  border-bottom: none;
}
.item-row input[type='checkbox'] {
  width: 20px;
  height: 20px;
  accent-color: var(--brand);
  flex-shrink: 0;
}
.item-row.checked {
  background: var(--brand-soft);
}
.item-name {
  flex: 1;
  color: var(--neutral-800);
}
.item-sub {
  width: 170px;
  font-size: 13px;
  color: var(--neutral-400);
}
.item-amount {
  width: 90px;
  text-align: right;
  font-weight: 600;
  color: var(--neutral-900);
}

/* ----- 权限提示条 ----- */
.auth-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: var(--space-3);
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: oklch(95% 0.04 60);
  color: var(--accent-deep);
  font-size: 14px;
  font-weight: 500;
}

/* ----- 订单操作 ----- */
.order-ops {
  display: flex;
  gap: var(--space-3);
}
.order-ops .big-btn {
  flex: 1;
  height: 50px;
  font-size: 17px;
}

/* ----- 退款确认弹窗 ----- */
.refund-dialog {
  text-align: center;
  padding: 8px 0;
}
.refund-label {
  font-size: 15px;
  color: var(--neutral-400);
  margin-bottom: 8px;
}
.refund-amount {
  font-size: 40px;
  font-weight: 700;
  color: var(--danger);
}
.refund-meta {
  margin-top: 14px;
  font-size: 14px;
  color: var(--neutral-500);
}
</style>
