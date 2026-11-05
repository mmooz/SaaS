<template>
  <div class="page">
    <!-- 顶部深色栏 -->
    <header class="page-header">
      <div class="header-title">交接班</div>
      <el-button class="back-btn" @click="$router.push('/')"><el-icon><ArrowLeft /></el-icon>&nbsp;返回收银台</el-button>
    </header>

    <div class="page-body">
      <!-- 当前班次信息卡 -->
      <section class="info-card">
        <div class="card-title">{{ shift ? '当前班次' : '尚未接班' }}</div>

        <!-- 未接班：填写现金底金后开班 -->
        <div v-if="!shift" class="open-box">
          <div class="open-tip">接班后才能开始收银，本班订单将归属该班次统计。</div>
          <div class="open-row">
            <span class="open-label">现金底金</span>
            <el-input-number v-model="baseCash" :min="0" :precision="2" :step="100" size="large" />
            <el-button type="primary" class="big-btn" :loading="loading" @click="doOpenShift">接 班</el-button>
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
          <el-button v-if="!settled" type="primary" class="big-btn handover-btn" :loading="loading" @click="doHandover">
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
        <el-button class="big-btn print-btn" @click="printSummary">
          <el-icon><Printer /></el-icon>&nbsp;打印交接小票
        </el-button>
      </section>

      <!-- 底部返回收银台 -->
      <div class="footer-actions">
        <el-button class="big-btn" @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>&nbsp;返回收银台
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Printer, Switch } from '@element-plus/icons-vue'
import { closeShift, fetchCurrentShift, fetchShiftSummary, openShift } from '../api'
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
 * 加载当前班次与本班汇总
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
    } else {
      store.setShiftId(null)
    }
  } catch (err) {
    ElMessage.error(`班次查询失败：${err.message}`)
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
    ElMessage.error(`接班失败：${err.message}`)
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
    const data = await closeShift(shift.value.id, { actualCash: Number(value) })
    applySummary(data)
    settled.value = true
    closeTime.value = formatTime(data.shift.end_at || new Date())
    store.setShiftId(null)
    ElMessage.success('交班成功，已生成本班汇总小票')
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

/* ----- 当前班次信息卡 ----- */
.info-card {
  background: #fff;
  border-radius: var(--radius-lg);
  border: 1px solid var(--neutral-200);
  box-shadow: var(--shadow-sm);
  padding: var(--space-4);
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
  font-size: 24px;
  color: var(--danger);
}
.handover-btn {
  width: 100%;
  height: 56px;
  font-size: 20px;
  letter-spacing: 6px;
}

/* ----- 未接班开班区 ----- */
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

/* ----- 交班汇总卡 ----- */
.summary-card {
  background: #fff;
  border-radius: var(--radius-lg);
  border: 1px solid var(--brand);
  box-shadow: var(--shadow-md);
  padding: var(--space-4);
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
}

/* ----- 底部操作 ----- */
.footer-actions {
  display: flex;
  justify-content: center;
}
</style>
