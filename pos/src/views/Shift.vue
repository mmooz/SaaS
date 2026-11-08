<template>
  <div class="shift-page">
    <!-- 当前班次信息卡 -->
    <section class="info-card">
      <div class="card-title">
        {{ shift ? (offlineShift ? '当前班次（离线）' : '当前班次') : '尚未接班' }}
      </div>

      <!-- 未接班：填写现金底金后开班 -->
      <div v-if="!shift" class="open-box">
        <div class="open-tip">接班后才能开始收银，本班订单将归属该班次统计。</div>
        <div class="open-row">
          <span class="open-label">现金底金</span>
          <el-input-number v-model="baseCash" :min="0" :precision="2" :step="100" />
          <el-button type="primary" :loading="loading" @click="doOpenShift">接 班</el-button>
        </div>
      </div>

      <!-- 已接班：展示本班实时汇总 -->
      <div v-else>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">收银员</div>
            <div class="info-value">{{ cashierName }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">接班时间</div>
            <div class="info-value num">{{ formatTime(shift.start_at) }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">当前订单数</div>
            <div class="info-value num">{{ summary.orders }} 单</div>
          </div>
          <div class="info-item">
            <div class="info-label">本班销售额</div>
            <div class="info-value num money">¥{{ summary.sales.toFixed(2) }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">现金收入</div>
            <div class="info-value num money">¥{{ summary.cash.toFixed(2) }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">现金应交</div>
            <div class="info-value num money">¥{{ summary.cashShould.toFixed(2) }}</div>
          </div>
        </div>
        <!-- 交接班大按钮（交班成功后隐藏） -->
        <el-button v-if="!settled" type="primary" class="handover-btn" :loading="loading" @click="doHandover">
          <el-icon><Switch /></el-icon>&nbsp;交 接 班
        </el-button>
      </div>
    </section>

    <!-- 交班成功汇总卡 -->
    <section v-if="settled" class="summary-card">
      <div class="summary-head">
        <div class="success-icon">✔</div>
        <div>
          <div class="card-title">交班成功</div>
          <div class="summary-time num">{{ closeTime }} · 已生成本班汇总小票</div>
        </div>
      </div>
      <!-- 各支付方式分行金额 -->
      <div class="summary-rows">
        <div class="sum-row">
          <span>订单总数</span>
          <span class="num">{{ summary.orders }} 单</span>
        </div>
        <div class="sum-row total">
          <span>本班销售额</span>
          <span class="num">¥{{ summary.sales.toFixed(2) }}</span>
        </div>
        <div class="sum-row" v-for="p in summary.payments" :key="p.method">
          <span>{{ p.method }}</span>
          <span class="num">¥{{ p.amount.toFixed(2) }}</span>
        </div>
        <div class="sum-row" v-if="summary.refund > 0">
          <span>退款金额</span>
          <span class="num">-¥{{ summary.refund.toFixed(2) }}</span>
        </div>
        <div class="sum-row">
          <span>现金应交（含底金）</span>
          <span class="num">¥{{ summary.cashShould.toFixed(2) }}</span>
        </div>
        <div class="sum-row" v-if="summary.actualCash !== null">
          <span>实际点钞</span>
          <span class="num">¥{{ summary.actualCash.toFixed(2) }}</span>
        </div>
      </div>
      <!-- 打印交接小票 -->
      <el-button class="print-btn" @click="printSummary">
        <el-icon><Printer /></el-icon>&nbsp;打印交接小票
      </el-button>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Printer, Switch } from '@element-plus/icons-vue'
import { closeShift, fetchCurrentShift, fetchShiftSummary, isNetworkError, openShift } from '../api'
import { offlineStore } from '../services/offline/OfflineStore'
import { offlineSnowflake } from '../services/offline/Snowflake'
import { PrintService } from '../services/print/PrintService'
import { PrintFormatter as F } from '../services/print/PrintFormatter'
import { usePosStore } from '../stores/posStore'

const store = usePosStore()

const loading = ref(false)
// 当前进行中的班次（null 表示未接班）
const shift = ref(null)
// 现金底金输入（接班用）
const baseCash = ref(500)
// 是否已交班
const settled = ref(false)
// 交班时间文案
const closeTime = ref('')
// 当前班次是否为本机离线班次
const offlineShift = ref(false)

// 本班汇总（页面展示用）
const summary = reactive({
  orders: 0,
  sales: 0,
  cash: 0,
  cashShould: 0,
  refund: 0,
  payments: [],
  actualCash: null,
})

// 收银员姓名
const cashierName = computed(() => (store.cashier ? store.cashier.name : '—'))

/**
 * 时间格式化（复用打印格式化工具）
 * @param {string|Date} value 时间
 * @returns {string} 格式化时间
 */
const formatTime = (value) => F.datetime(value)

/**
 * 应用服务端班次汇总到页面展示数据
 * @param {object} data 班次汇总响应
 */
const applySummary = (data) => {
  summary.orders = data.order_count || 0
  summary.sales = Number(data.total_sales) || 0
  summary.refund = Number(data.refund_amount) || 0
  summary.cashShould = Number(data.cash_should) || 0
  summary.actualCash = data.actual_cash ?? null
  summary.payments = (data.payments || []).map((p) => ({
    method: p.method,
    amount: Number(p.amount) || 0,
    count: p.count || 0,
  }))
  summary.cash = summary.payments.find((p) => p.method === '现金')?.amount || 0
}

/**
 * 按本机订单统计班次汇总（离线交班时使用）
 * @param {string} shiftId 班次 ID
 * @returns {Promise<void>}
 */
const loadLocalSummary = async (shiftId) => {
  const orders = await offlineStore.listOrdersByShift(shiftId)
  const payments = new Map()
  let sales = 0
  let refund = 0
  for (const order of orders) {
    sales += Number(order.total_amount) || 0
    refund += Number(order.refunded_amount) || 0
    try {
      const detail = JSON.parse(order.pay_details || '{}')
      for (const [method, amount] of Object.entries(detail)) {
        payments.set(method, (payments.get(method) || 0) + (Number(amount) || 0))
      }
    } catch {
      // 支付明细损坏时跳过该单，不影响其余统计
    }
  }
  summary.orders = orders.length
  summary.sales = +sales.toFixed(2)
  summary.refund = +refund.toFixed(2)
  summary.payments = [...payments.entries()].map(([method, amount]) => ({
    method,
    amount: +amount.toFixed(2),
    count: 0,
  }))
  const cash = summary.payments.find((p) => p.method === '现金')?.amount || 0
  summary.cash = cash
  summary.cashShould = +(Number(shift.value?.base_cash || 0) + cash).toFixed(2)
  summary.actualCash = null
}

/**
 * 加载当前班次与本班汇总（网络不可用时回退到本机班次）
 * @returns {Promise<void>}
 */
const loadShift = async () => {
  if (!store.cashier) {
    ElMessage.warning('请先登录后再接班')
    return
  }
  loading.value = true
  try {
    const current = await fetchCurrentShift(store.cashier.id)
    shift.value = current
    if (current) {
      store.setShiftId(current.id)
      const data = await fetchShiftSummary(current.id)
      applySummary(data)
      // 同步一份本机快照，供断网时交班使用
      await offlineStore.saveLocalShift({
        id: current.id,
        cashier_id: current.cashier_id,
        start_at: current.start_at,
        base_cash: current.base_cash,
        total_sales: data.total_sales,
        order_count: data.order_count,
        status: 'open',
        synced: true,
      })
    } else {
      store.setShiftId(null)
    }
    offlineShift.value = false
  } catch (err) {
    // 非网络异常（如接口报错）直接提示，避免误建离线班次
    if (!isNetworkError(err)) {
      ElMessage.error(`班次查询失败：${err.message}`)
      return
    }
    // 网络异常：载入本机进行中的班次，保证离线也能交班
    const local = await offlineStore.getOpenShift(store.cashier.id)
    if (local) {
      shift.value = {
        id: local.shift_id,
        cashier_id: local.cashier_id,
        start_at: local.start_at,
        base_cash: local.base_cash,
        status: 'open',
      }
      offlineShift.value = true
      store.setShiftId(local.shift_id)
      await loadLocalSummary(local.shift_id)
      ElMessage.warning('网络不可用，已载入本机班次（离线统计）')
    } else {
      ElMessage.warning(`班次查询失败，可离线接班：${err.message}`)
    }
  } finally {
    loading.value = false
  }
}

/**
 * 接班：创建班次并写入本地班次 ID
 * @returns {Promise<void>}
 */
const doOpenShift = async () => {
  if (!store.cashier) {
    ElMessage.warning('请先登录后再接班')
    return
  }
  loading.value = true
  try {
    const created = await openShift({ cashierId: store.cashier.id, baseCash: baseCash.value })
    shift.value = created
    store.setShiftId(created.id)
    settled.value = false
    const data = await fetchShiftSummary(created.id)
    applySummary(data)
    ElMessage.success('接班成功，本班订单将自动归属统计')
  } catch (err) {
    // 非网络异常直接提示，避免重复创建班次
    if (!isNetworkError(err)) {
      ElMessage.error(`接班失败：${err.message}`)
      return
    }
    // 网络不可用：本机接班，联网后由补传队列同步到后台
    const localShift = {
      id: offlineSnowflake.nextId(),
      cashier_id: store.cashier.id,
      start_at: new Date().toISOString(),
      base_cash: baseCash.value,
      total_sales: 0,
      order_count: 0,
      status: 'open',
      synced: false,
    }
    await offlineStore.saveLocalShift(localShift)
    shift.value = localShift
    offlineShift.value = true
    store.setShiftId(localShift.id)
    await loadLocalSummary(localShift.id)
    settled.value = false
    ElMessage.warning(`网络不可用，已本机接班，联网后自动补传（${err.message}）`)
  } finally {
    loading.value = false
  }
}

/**
 * 交接班：点钞确认后调用交班接口并展示汇总
 * @returns {Promise<void>}
 */
const doHandover = async () => {
  if (!shift.value) return
  try {
    const { value } = await ElMessageBox.prompt(
      `现金应交 ¥${summary.cashShould.toFixed(2)}，请输入实际点钞金额`,
      '交接班',
      {
        confirmButtonText: '确认交接',
        cancelButtonText: '取消',
        inputValue: summary.cashShould.toFixed(2),
        inputPattern: /^\d+(\.\d{1,2})?$/,
        inputErrorMessage: '请输入有效金额',
      },
    )
    loading.value = true
    try {
      const data = await closeShift(shift.value.id, { actualCash: Number(value) })
      applySummary(data)
      summary.actualCash = Number(value)
      settled.value = true
      closeTime.value = formatTime(data.shift.end_at || new Date())
      // 本机班次同步为已交班
      await offlineStore.saveLocalShift({
        id: shift.value.id,
        cashier_id: shift.value.cashier_id,
        start_at: shift.value.start_at,
        end_at: data.shift.end_at,
        base_cash: shift.value.base_cash,
        total_sales: summary.sales,
        order_count: summary.orders,
        status: 'closed',
        synced: true,
      })
      store.setShiftId(null)
      offlineShift.value = false
      ElMessage.success('交班成功，已生成本班汇总小票')
    } catch (err) {
      // 非网络异常交由外层提示，避免把服务端拒绝误判为离线
      if (!isNetworkError(err)) throw err
      // 网络不可用：按本机订单统计并本地交班，班次进入补传队列
      await loadLocalSummary(shift.value.id)
      const endAt = new Date().toISOString()
      summary.actualCash = Number(value)
      await offlineStore.saveLocalShift({
        id: shift.value.id,
        cashier_id: shift.value.cashier_id,
        start_at: shift.value.start_at,
        end_at: endAt,
        base_cash: shift.value.base_cash,
        total_sales: summary.sales,
        order_count: summary.orders,
        status: 'closed',
        synced: false,
      })
      settled.value = true
      closeTime.value = formatTime(endAt)
      store.setShiftId(null)
      offlineShift.value = false
      ElMessage.warning(`网络不可用，已本机交班（离线统计），联网后自动补传：${err.message}`)
    }
  } catch (err) {
    // 用户取消弹窗时不提示错误
    if (err !== 'cancel' && err?.message) ElMessage.error(`交班失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

// 打印交接小票：使用本次交班真实汇总数据
const printSummary = () => {
  if (!shift.value) return
  PrintService.printShift({
    cashierName: cashierName.value,
    shiftName: '当班',
    startTime: formatTime(shift.value.start_at),
    endTime: closeTime.value,
    orderCount: summary.orders,
    totalAmount: summary.sales,
    payments: summary.payments.map((p) => ({ method: p.method, amount: p.amount, count: p.count })),
    openingCash: Number(shift.value.base_cash) || 0,
    cashShould: summary.cashShould,
  })
}

onMounted(loadShift)
</script>

<style scoped>
.shift-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 当前班次信息卡（与管理页卡片一致） */
.info-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
}
.card-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--neutral-900);
  margin-bottom: var(--space-3);
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.info-item {
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}
.info-label {
  font-size: 13px;
  color: var(--neutral-400);
  margin-bottom: 6px;
}
.info-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--neutral-900);
}
.info-value.money {
  color: var(--danger);
}
.handover-btn {
  width: 100%;
  height: 48px;
  font-size: 17px;
  letter-spacing: 6px;
}

/* 未接班开班区 */
.open-box {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.open-tip {
  font-size: 14px;
  color: var(--neutral-500);
}
.open-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.open-label {
  font-size: 15px;
  color: var(--neutral-600);
}

/* 交班汇总卡（保持品牌色高亮，但圆角/阴影与管理页一致） */
.summary-card {
  background: #fff;
  border: 1px solid var(--brand);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
}
.summary-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.success-icon {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--brand-soft);
  color: var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 700;
}
.summary-time {
  font-size: 13px;
  color: var(--neutral-400);
  margin-top: 4px;
}
.summary-rows {
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: var(--space-4);
}
.sum-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px var(--space-3);
  border-bottom: 1px solid var(--neutral-100);
  font-size: 16px;
  color: var(--neutral-700);
}
.sum-row:last-child {
  border-bottom: none;
}
.sum-row.total {
  background: var(--brand-soft);
  color: var(--brand-deep);
  font-weight: 700;
  font-size: 18px;
}
.print-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
}
</style>
