<template>
  <div class="dashboard">
    <!-- 顶部统计卡片 -->
    <div class="stat-grid" v-loading="loading">
      <div class="stat-card">
        <div class="stat-icon" style="--c: var(--brand)"><el-icon :size="22"><Money /></el-icon></div>
        <div>
          <div class="stat-label">今日销售额</div>
          <div class="stat-value num">¥ {{ today.sales.toFixed(2) }}</div>
          <div class="stat-trend" :class="{ up: salesCompare.up }">{{ salesCompare.text }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="--c: var(--info)"><el-icon :size="22"><Tickets /></el-icon></div>
        <div>
          <div class="stat-label">今日订单数</div>
          <div class="stat-value num">{{ today.orders }}</div>
          <div class="stat-trend" :class="{ up: orderCompare.up }">{{ orderCompare.text }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="--c: var(--accent)"><el-icon :size="22"><ScaleToOriginal /></el-icon></div>
        <div>
          <div class="stat-label">今日称重单数</div>
          <div class="stat-value num">{{ today.weighted_orders }}</div>
          <div class="stat-trend">占比 {{ weightedRatio }}%</div>
        </div>
      </div>
      <div class="stat-card warn">
        <div class="stat-icon" style="--c: var(--danger)"><el-icon :size="22"><Warning /></el-icon></div>
        <div>
          <div class="stat-label">低库存预警</div>
          <div class="stat-value num">{{ alertTotal }}</div>
          <div class="stat-trend danger">需尽快补货</div>
        </div>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="chart-row">
      <div class="chart-card span-2">
        <div class="card-head">
          <h3>近 7 日销售趋势</h3>
          <el-radio-group v-model="trendRange" size="small">
            <el-radio-button value="7">近7日</el-radio-button>
            <el-radio-button value="30">近30日</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="trendRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <div class="card-head">
          <h3>分类销售占比</h3>
        </div>
        <div ref="cateRef" class="chart-box"></div>
      </div>
    </div>

    <!-- 预警 + 订单列表 -->
    <div class="chart-row">
      <div class="chart-card">
        <div class="card-head">
          <h3>低库存预警</h3>
          <el-button link type="primary" size="small" @click="$router.push('/inventory')">去补货 →</el-button>
        </div>
        <div class="warn-list">
          <div v-for="w in warnings" :key="w.product_id" class="warn-item">
            <div class="warn-info">
              <span class="warn-name">{{ w.name }}</span>
              <span class="warn-amount num">剩 {{ w.stock }}{{ w.unit }} / 安全 {{ w.safety_stock }}</span>
            </div>
            <el-tag size="small" :type="w.status === 'out' ? 'danger' : 'warning'" effect="light">
              {{ w.status === 'out' ? '已售罄' : '库存不足' }}
            </el-tag>
          </div>
          <div v-if="!warnings.length && !loading" class="warn-empty">暂无库存预警</div>
        </div>
      </div>
      <div class="chart-card span-2">
        <div class="card-head">
          <h3>最近订单</h3>
          <el-button link type="primary" size="small" @click="$router.push('/reports')">查看全部 →</el-button>
        </div>
        <el-table :data="recentOrders" size="small" class="order-table" empty-text="暂无订单">
          <el-table-column prop="orderNo" label="单号" width="150" />
          <el-table-column prop="items" label="商品" min-width="180">
            <template #default="{ row }">{{ row.items }}</template>
          </el-table-column>
          <el-table-column prop="payMethod" label="支付" width="90" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="payTagType(row.payMethod)" effect="light">{{ row.payMethod }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="金额" width="100" align="right">
            <template #default="{ row }"><span class="num">¥{{ row.amount.toFixed(2) }}</span></template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="80" align="right">
            <template #default="{ row }"><span class="cell-time">{{ row.time }}</span></template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Money, Tickets, ScaleToOriginal, Warning } from '@element-plus/icons-vue'
import { fetchDailyReport, fetchInventoryAlerts, fetchOrders, fetchProfitReport } from '../api'

// 图表颜色（与报表中心保持一致）
const COLORS = { green: '#2F9E5F', orange: '#F5A623', blue: '#4A90D9', red: '#E05B4D' }
// 分类饼图配色
const PIE_COLORS = ['#2F9E5F', '#F5A623', '#E05B4D', '#4A90D9', '#8A8F3B', '#9B59B6', '#16A085']

// 趋势图容器
const trendRef = ref(null)
// 分类饼图容器
const cateRef = ref(null)
// 趋势区间：7 或 30 天
const trendRange = ref('7')
// 页面加载状态
const loading = ref(false)

// 今日汇总
const today = ref({ sales: 0, orders: 0, avg_price: 0, weight_kg: 0, weighted_orders: 0 })
// 昨日汇总（用于同比）
const yesterday = ref({ sales: 0, orders: 0 })
// 低库存预警列表
const warnings = ref([])
// 低库存预警总数
const alertTotal = ref(0)
// 最近订单列表
const recentOrders = ref([])
// 分类销售数据（饼图用）
const categorySales = ref([])
// 趋势图数据
const trendData = ref({ labels: [], values: [] })

/**
 * 数字补零
 * @param {number} n 数字
 * @returns {string} 两位字符串
 */
const pad = (n) => String(n).padStart(2, '0')

/**
 * 以今天为基准偏移若干天，返回 YYYY-MM-DD
 * @param {number} offset 偏移天数（负数表示过去）
 * @returns {string} 日期字符串
 */
const dateStr = (offset) => {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/**
 * 获取或初始化 ECharts 实例（避免重复初始化）
 * @param {HTMLElement} el 图表容器
 * @returns {object} ECharts 实例
 */
const getChart = (el) => echarts.getInstanceByDom(el) || echarts.init(el)

// 销售额较昨日变化
const salesCompare = computed(() => {
  const prev = yesterday.value.sales
  const cur = today.value.sales
  if (!prev) return { text: cur > 0 ? '昨日无销售' : '较昨日 —', up: false }
  const pct = ((cur - prev) / prev) * 100
  return { text: `较昨日 ${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`, up: pct >= 0 }
})

// 订单数较昨日变化
const orderCompare = computed(() => {
  const diff = today.value.orders - yesterday.value.orders
  return { text: `较昨日 ${diff >= 0 ? '+' : ''}${diff} 单`, up: diff >= 0 }
})

// 称重订单占比
const weightedRatio = computed(() =>
  today.value.orders ? ((today.value.weighted_orders / today.value.orders) * 100).toFixed(1) : '0.0',
)

/**
 * 把日报趋势补齐为连续日期（缺失日期补 0）
 * @param {Array<{label: string, sales: number}>} points 后端趋势点
 * @param {number} days 天数
 * @returns {{labels: string[], values: number[]}} 连续趋势
 */
function fillTrend(points, days) {
  const map = new Map(points.map((p) => [p.label, p.sales]))
  const labels = []
  const values = []
  for (let i = days - 1; i >= 0; i--) {
    const label = dateStr(-i).slice(5)
    labels.push(label)
    values.push(Number(map.get(label) || 0))
  }
  return { labels, values }
}

/**
 * 解析支付明细为支付方式文本
 * @param {string|null} raw 支付明细 JSON
 * @returns {string} 支付方式文本
 */
function payMethodText(raw) {
  try {
    const parsed = JSON.parse(raw || '{}')
    const names = Object.entries(parsed)
      .filter(([, amount]) => Number(amount) > 0)
      .map(([name]) => name)
    return names.length ? names.join('+') : '—'
  } catch {
    return '—'
  }
}

/**
 * 支付方式对应的标签类型
 * @param {string} method 支付方式
 * @returns {string} Element Plus 标签类型
 */
function payTagType(method) {
  if (method === '现金') return 'warning'
  if (method === '储值') return 'success'
  return 'primary'
}

/**
 * 把后端订单转为首页订单行
 * @param {object} order 订单数据
 * @returns {object} 表格行
 */
function toOrderRow(order) {
  const items = (order.items || []).map((it) =>
    it.is_weighted ? `${it.name} ×${Number(it.weight_kg || 0)}kg` : `${it.name} ×${Number(it.qty || 0)}`,
  )
  return {
    orderNo: order.order_no,
    items: items.length ? items.join('、') : '—',
    payMethod: payMethodText(order.pay_details),
    amount: Number(order.total_amount || 0),
    time: (order.created_at || '').slice(11, 16),
  }
}

/**
 * 加载首页全部数据并渲染图表
 */
async function loadDashboard() {
  loading.value = true
  const days = Number(trendRange.value)
  try {
    const [dayReport, prevReport, rangeReport, alerts, orders, profit] = await Promise.all([
      fetchDailyReport({ start: dateStr(0), end: dateStr(0), mode: 'day' }),
      fetchDailyReport({ start: dateStr(-1), end: dateStr(-1), mode: 'day' }),
      fetchDailyReport({ start: dateStr(-(days - 1)), end: dateStr(0), mode: 'day' }),
      fetchInventoryAlerts(),
      fetchOrders({ page: 1, pageSize: 6 }),
      fetchProfitReport({ start: dateStr(-(days - 1)), end: dateStr(0) }),
    ])
    today.value = dayReport.summary
    yesterday.value = prevReport.summary
    warnings.value = (alerts.items || []).slice(0, 6)
    alertTotal.value = alerts.total ?? warnings.value.length
    recentOrders.value = (orders.items || []).map(toOrderRow)
    categorySales.value = profit.categories || []
    trendData.value = fillTrend(rangeReport.trend || [], days)
  } catch (err) {
    ElMessage.error(`首页数据加载失败：${err.message}`)
  } finally {
    loading.value = false
  }
  await nextTick()
  renderTrend()
  renderCategory()
}

/**
 * 渲染销售趋势折线图
 */
function renderTrend() {
  if (!trendRef.value) return
  const chart = getChart(trendRef.value)
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: trendData.value.labels,
        axisLine: { lineStyle: { color: '#c9c9c9' } },
        // 30 天区间强制显示全部日期刻度并倾斜，避免自动隐藏
        axisLabel: { color: '#8a8a8a', interval: 0, rotate: Number(trendRange.value) > 7 ? 45 : 0 },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f0f0f0' } },
        axisLabel: { color: '#8a8a8a' },
      },
      series: [
        {
          name: '销售额',
          type: 'line',
          smooth: true,
          data: trendData.value.values,
          itemStyle: { color: COLORS.green },
          lineStyle: { width: 3 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(47,158,95,0.25)' },
                { offset: 1, color: 'rgba(47,158,95,0.02)' },
              ],
            },
          },
        },
      ],
    },
    true,
  )
}

/**
 * 渲染分类销售占比饼图
 */
function renderCategory() {
  if (!cateRef.value) return
  const chart = getChart(cateRef.value)
  // 过滤零销售额分类，避免图例出现空分类
  const data = categorySales.value
    .filter((c) => c.sales > 0)
    .map((c, index) => ({
      value: c.sales,
      name: c.category,
      itemStyle: { color: PIE_COLORS[index % PIE_COLORS.length] },
    }))
  chart.setOption(
    {
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      legend: { bottom: 0, icon: 'circle', itemWidth: 8, textStyle: { color: '#555' } },
      title: {
        show: !data.length,
        text: '暂无销售数据',
        left: 'center',
        top: '45%',
        textStyle: { color: '#bbb', fontSize: 13, fontWeight: 'normal' },
      },
      series: [
        {
          name: '分类占比',
          type: 'pie',
          radius: ['42%', '70%'],
          center: ['50%', '45%'],
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          data,
        },
      ],
    },
    true,
  )
}

// 切换 7 日 / 30 日时重新加载
watch(trendRange, loadDashboard)

onMounted(loadDashboard)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.stat-card {
  background: #fff;
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--neutral-200);
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: color-mix(in oklch, var(--c) 12%, white);
  color: var(--c);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-label {
  font-size: 13px;
  color: var(--neutral-500);
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--neutral-900);
  line-height: 1.3;
}
.stat-trend {
  font-size: 12px;
  color: var(--neutral-400);
}
.stat-trend.up { color: var(--success); }
.stat-trend.danger { color: var(--danger); }
.chart-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.chart-card {
  background: #fff;
  border-radius: var(--radius-md);
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--neutral-200);
}
.chart-card.span-2 {
  grid-column: span 2;
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
.chart-box {
  height: 260px;
}
.warn-list {
  display: flex;
  flex-direction: column;
}
.warn-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--neutral-100);
}
.warn-item:last-child {
  border-bottom: none;
}
.warn-empty {
  padding: 24px 0;
  text-align: center;
  font-size: 13px;
  color: var(--neutral-400);
}
.warn-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-700);
}
.warn-amount {
  display: block;
  font-size: 12px;
  color: var(--neutral-400);
}
.order-table {
  width: 100%;
}
.cell-time {
  color: var(--neutral-400);
  font-size: 12px;
}
</style>
