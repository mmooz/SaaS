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
        <div class="card-title">当前班次</div>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">收银员</div>
            <div class="info-value">{{ shift.cashier }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">接班时间</div>
            <div class="info-value num">{{ shift.startTime }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">当前订单数</div>
            <div class="info-value num">{{ shift.orderCount }} 单</div>
          </div>
          <div class="info-item">
            <div class="info-label">本班销售额</div>
            <div class="info-value num money">¥{{ shift.salesAmount.toFixed(2) }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">现金金额</div>
            <div class="info-value num money">¥{{ shift.cashAmount.toFixed(2) }}</div>
          </div>
        </div>
        <!-- 交接班大按钮（交班成功后隐藏） -->
        <el-button v-if="!settled" type="primary" class="big-btn handover-btn" @click="doHandover">
          <el-icon><Switch /></el-icon>&nbsp;交 接 班
        </el-button>
      </section>

      <!-- 交班成功汇总卡 -->
      <section v-if="settled" class="summary-card">
        <div class="summary-head">
          <div class="success-icon">✔</div>
          <div>
            <div class="card-title">交班成功</div>
            <div class="summary-time num">2026-11-05 15:30 · 已生成本班汇总小票</div>
          </div>
        </div>
        <!-- 各支付方式分行金额 -->
        <div class="summary-rows">
          <div class="sum-row">
            <span>订单总数</span>
            <span class="num">{{ summary.orderCount }} 单</span>
          </div>
          <div class="sum-row total">
            <span>本班销售额</span>
            <span class="num">¥{{ summary.salesAmount.toFixed(2) }}</span>
          </div>
          <div class="sum-row">
            <span>微信</span>
            <span class="num">¥{{ summary.wechat.toFixed(2) }}</span>
          </div>
          <div class="sum-row">
            <span>支付宝</span>
            <span class="num">¥{{ summary.alipay.toFixed(2) }}</span>
          </div>
          <div class="sum-row">
            <span>现金</span>
            <span class="num">¥{{ summary.cash.toFixed(2) }}</span>
          </div>
          <div class="sum-row">
            <span>储值</span>
            <span class="num">¥{{ summary.storedValue.toFixed(2) }}</span>
          </div>
        </div>
        <!-- 打印交接小票（示意） -->
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
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Printer, Switch } from '@element-plus/icons-vue'
import { PrintService } from '../services/print/PrintService'

// 当前班次信息（模拟数据）
const shift = reactive({
  cashier: '收银员 小李',
  startTime: '2026-11-05 08:00',
  orderCount: 128,
  salesAmount: 8652.4,
  cashAmount: 2350.0,
})

const settled = ref(false) // 是否已交班

// 交班汇总数据（模拟数据）
const summary = reactive({
  orderCount: 128,
  salesAmount: 8652.4,
  wechat: 3421.6,
  alipay: 1878.8,
  cash: 2350.0,
  storedValue: 1002.0,
})

// 交接班：弹窗确认后展示交班汇总卡
const doHandover = () => {
  ElMessageBox.confirm('确认交接？交接后将打印本班汇总小票', '交接班', {
    confirmButtonText: '确认交接',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      settled.value = true
      ElMessage.success('交接成功，已生成本班汇总小票')
    })
    .catch(() => {})
}

// 打印交接小票：组装本班汇总数据后调用打印通道
const printSummary = () => {
  const payments = [
    { method: '现金', amount: summary.cash, count: 0 },
    { method: '微信', amount: summary.wechat, count: 0 },
    { method: '支付宝', amount: summary.alipay, count: 0 },
    { method: '储值', amount: summary.storedValue, count: 0 },
  ]
  PrintService.printShift({
    cashierName: shift.cashier,
    shiftName: '早班',
    startTime: shift.startTime,
    endTime: new Date(),
    orderCount: summary.orderCount,
    totalAmount: summary.salesAmount,
    payments,
    openingCash: 500,
    cashShould: 500 + payments[0].amount,
  })
  ElMessage.success('已发送交班汇总单到打印机')
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
