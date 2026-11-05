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
        <el-button type="primary" class="big-btn search-btn" :loading="loading" @click="doSearch">搜 索</el-button>
      </div>

      <!-- 无结果提示 -->
      <div v-if="showEmptyTip" class="empty-tip">未找到相关订单，请核对单号或手机号</div>

      <!-- 订单结果卡 -->
      <section v-for="o in resultOrders" :key="o.orderNo" class="order-card">
        <div class="order-head">
          <div>
            <div class="order-no">
              {{ o.orderNo }}
              <span class="order-status" :class="o.status">{{ statusText(o.status) }}</span>
            </div>
            <div class="order-meta">
              {{ o.time }} · {{ o.payMethod }} · {{ o.cashier }}
              <span v-if="o.mobile"> · {{ o.mobile }}</span>
            </div>
          </div>
          <div class="order-amount num">¥{{ o.amount.toFixed(2) }}</div>
        </div>

        <!-- 已退款金额提示 -->
        <div v-if="o.refundedAmount > 0" class="refunded-tip">
          已退款 ¥{{ o.refundedAmount.toFixed(2) }}，剩余可退 ¥{{ remainingAmount(o).toFixed(2) }}
        </div>

        <!-- 商品明细列表：勾选商品后可用于单项退货 -->
        <div class="item-list">
          <label
            v-for="item in o.items"
            :key="item.id"
            class="item-row"
            :class="{ checked: isChecked(o, item), disabled: item.refunded }"
          >
            <input
              type="checkbox"
              :checked="isChecked(o, item)"
              :disabled="item.refunded"
              @change="toggleItem(o, item)"
            />
            <span class="item-name">
              {{ item.name }}
              <span v-if="item.refunded" class="item-refunded">已退货</span>
            </span>
            <span class="item-sub num">{{ item.weighted ? `${item.weight}kg × ¥${item.price.toFixed(2)}` : `× ${item.qty}` }}</span>
            <span class="item-amount num">¥{{ item.amount.toFixed(2) }}</span>
          </label>
        </div>

        <!-- 权限提示：非本人当班订单需要店长授权 -->
        <div v-if="!o.isSelf" class="auth-tip">
          <el-icon><WarningFilled /></el-icon>&nbsp;该订单非本人当班，退款需要店长授权
        </div>

        <div class="order-ops">
          <el-button
            type="danger"
            class="big-btn"
            :disabled="o.status === 'refunded'"
            @click="openRefund(o, 'full')"
          >整单退款</el-button>
          <el-button
            class="big-btn"
            :disabled="!hasChecked(o)"
            @click="openRefund(o, 'item')"
          >单项退货</el-button>
        </div>
      </section>
    </div>

    <!-- 店长授权弹窗 -->
    <el-dialog v-model="authDialog" title="店长授权" width="380px">
      <el-form label-width="70px">
        <el-form-item label="账号">
          <el-input v-model="authForm.username" placeholder="请输入店长/管理员账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="authForm.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button class="big-btn" @click="authDialog = false">取 消</el-button>
        <el-button type="primary" class="big-btn" :loading="authLoading" @click="authorizeManager">授 权</el-button>
      </template>
    </el-dialog>

    <!-- 退款确认弹窗 -->
    <el-dialog v-model="refundDialog" :title="refundType === 'full' ? '整单退款' : '单项退货'" width="420px">
      <div class="refund-dialog">
        <div class="refund-label">退款金额</div>
        <div class="refund-amount num">¥{{ refundAmount.toFixed(2) }}</div>
        <div class="refund-meta">原支付方式：{{ currentOrder?.payMethod }} · 退款将原路退回</div>
        <el-input
          v-model="refundReason"
          class="reason-input"
          placeholder="退款原因（选填）"
          maxlength="60"
        />
      </div>
      <template #footer>
        <el-button class="big-btn" @click="refundDialog = false">取 消</el-button>
        <el-button type="danger" class="big-btn" :loading="submitting" @click="confirmRefund">确认退款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Search, WarningFilled } from '@element-plus/icons-vue'
import { fetchOrders, login, refundOrder } from '../api'
import { usePosStore } from '../stores/posStore'
import { OrderPrintMapper } from '../services/print/OrderPrintMapper'
import { PrintFormatter as F } from '../services/print/PrintFormatter'

const store = usePosStore()

const keyword = ref('')
const loading = ref(false)
const submitting = ref(false)
// 服务端返回的订单列表（已转换为页面展示模型）
const orders = ref([])

// 搜索结果：服务端已按关键字过滤，前端不再重复过滤
const resultOrders = computed(() => orders.value)

// 无结果提示：已加载且无订单时显示
const showEmptyTip = computed(() => !loading.value && orders.value.length === 0)

// 订单状态文案
const statusText = (status) => {
  if (status === 'refunded') return '已全额退款'
  if (status === 'partially_refunded') return '部分退款'
  return '已结算'
}

/**
 * 服务端订单转页面展示模型
 * @param {object} order 服务端订单（OrderOut）
 * @returns {object} 展示模型
 */
const toDisplay = (order) => ({
  orderNo: order.order_no,
  time: F.datetime(order.created_at),
  mobile: order.member_mobile || '',
  payMethod: OrderPrintMapper.payMethod(order.pay_details),
  cashierId: order.cashier_id,
  cashier: order.cashier_id ? `收银员#${order.cashier_id}` : '—',
  isSelf: !!store.cashier && order.cashier_id === store.cashier.id,
  status: order.status,
  amount: Number(order.total_amount) || 0,
  refundedAmount: Number(order.refunded_amount) || 0,
  items: (order.items || []).map((item) => ({
    id: item.id,
    name: item.name,
    weighted: !!item.is_weighted,
    weight: Number(item.weight_kg || 0).toFixed(2),
    qty: item.qty,
    price: Number(item.unit_price) || 0,
    amount: Number(item.amount) || 0,
    refunded: !!item.refunded,
  })),
})

/**
 * 加载订单列表
 * @returns {Promise<void>}
 */
const loadOrders = async () => {
  loading.value = true
  try {
    const data = await fetchOrders({ keyword: keyword.value.trim(), pageSize: 20 })
    orders.value = (data.items || []).map(toDisplay)
  } catch (err) {
    ElMessage.error(`订单查询失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

// 点击搜索：按订单号/手机号重新查询
const doSearch = () => loadOrders()

// 剩余可退金额（整单退款按剩余应收计算）
const remainingAmount = (o) => Math.max(0, +(o.amount - o.refundedAmount).toFixed(2))

// 勾选集合：订单号::明细ID -> 是否勾选（用于单项退货）
const checkedMap = ref({})

const isChecked = (o, item) => checkedMap.value[`${o.orderNo}::${item.id}`] === true

// 切换商品勾选状态（已退货商品不可勾选）
const toggleItem = (o, item) => {
  if (item.refunded) return
  const key = `${o.orderNo}::${item.id}`
  checkedMap.value[key] = !checkedMap.value[key]
}

// 当前订单是否存在可退且已勾选的商品
const hasChecked = (o) =>
  o.status !== 'refunded' && o.items.some((i) => !i.refunded && isChecked(o, i))

// 退款弹窗状态
const refundDialog = ref(false)
const refundType = ref('full') // full=整单退款 item=单项退货
const currentOrder = ref(null)
const refundAmount = ref(0)
const refundReason = ref('')

// 店长授权弹窗状态
const authDialog = ref(false)
const authLoading = ref(false)
const authForm = ref({ username: '', password: '' })
// 待执行的退款动作（授权通过后继续）
let pendingRefund = null

/**
 * 打开退款确认弹窗：整单退剩余金额，单项退勾选商品合计
 * @param {object} o 订单展示模型
 * @param {string} type full=整单退款 item=单项退货
 */
const prepareRefund = (o, type) => {
  currentOrder.value = o
  refundType.value = type
  refundReason.value = ''
  if (type === 'full') {
    refundAmount.value = remainingAmount(o)
  } else {
    const sum = o.items.reduce((s, i) => (isChecked(o, i) && !i.refunded ? s + i.amount : s), 0)
    refundAmount.value = Math.min(+(sum.toFixed(2)), remainingAmount(o))
  }
  refundDialog.value = true
}

// 当前操作的授权人 ID（非本人订单退款时记录）
let authorizerId = null

/**
 * 打开退款：本人当班订单直接确认；否则先走店长授权
 * @param {object} o 订单展示模型
 * @param {string} type 退款类型
 */
const openRefund = (o, type) => {
  if (o.isSelf) {
    authorizerId = null
    prepareRefund(o, type)
    return
  }
  pendingRefund = { order: o, type }
  authForm.value = { username: '', password: '' }
  authDialog.value = true
}

/**
 * 店长授权：校验账号角色为店长/管理员后继续退款流程
 * @returns {Promise<void>}
 */
const authorizeManager = async () => {
  if (!authForm.value.username || !authForm.value.password) {
    ElMessage.warning('请输入账号与密码')
    return
  }
  authLoading.value = true
  try {
    const res = await login(authForm.value.username, authForm.value.password)
    if (!['admin', 'manager'].includes(res.user.role)) {
      ElMessage.warning('该账号不是店长或管理员，无法授权')
      return
    }
    authorizerId = res.user.id
    authDialog.value = false
    if (pendingRefund) {
      prepareRefund(pendingRefund.order, pendingRefund.type)
      pendingRefund = null
    }
  } catch (err) {
    ElMessage.error(`授权失败：${err.message}`)
  } finally {
    authLoading.value = false
  }
}

// 确认退款：调用后端退款接口并刷新列表
const confirmRefund = async () => {
  if (!currentOrder.value) return
  submitting.value = true
  try {
    const itemIds = refundType.value === 'item'
      ? currentOrder.value.items
        .filter((i) => !i.refunded && isChecked(currentOrder.value, i))
        .map((i) => i.id)
      : []
    const record = await refundOrder(currentOrder.value.orderNo, {
      refundType: refundType.value,
      itemIds,
      reason: refundReason.value.trim(),
      cashierId: store.cashier ? store.cashier.id : null,
      authorizerId,
    })
    ElMessage.success(`退款成功，金额 ¥${Number(record.amount).toFixed(2)}`)
    refundDialog.value = false
    checkedMap.value = {}
    await loadOrders()
  } catch (err) {
    ElMessage.error(`退款失败：${err.message}`)
  } finally {
    submitting.value = false
  }
}

onMounted(loadOrders)
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
.order-status {
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: var(--brand-soft);
  color: var(--brand);
}
.order-status.refunded {
  background: var(--neutral-100);
  color: var(--neutral-500);
}
.order-status.partially_refunded {
  background: oklch(95% 0.04 60);
  color: var(--accent-deep);
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
.refunded-tip {
  margin-bottom: var(--space-3);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--neutral-50);
  color: var(--neutral-500);
  font-size: 13px;
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
.item-row.disabled {
  cursor: not-allowed;
  color: var(--neutral-400);
}
.item-refunded {
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--neutral-100);
  color: var(--neutral-400);
  font-size: 12px;
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
.reason-input {
  margin-top: 14px;
}
</style>
