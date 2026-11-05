<template>
  <div class="reports">
    <!-- 页头：日期范围 + 报表类型 tab + 导出按钮 -->
    <div class="page-head card">
      <div class="head-left">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 240px"
        />
        <el-radio-group v-model="reportType" size="default">
          <el-radio-button value="daily">销售日报月报</el-radio-button>
          <el-radio-button value="rank">商品销售排行</el-radio-button>
          <el-radio-button value="hourly">时段分析</el-radio-button>
          <el-radio-button value="profit">毛利分析</el-radio-button>
          <el-radio-button value="member">会员分析</el-radio-button>
        </el-radio-group>
      </div>
      <el-button type="primary" plain :icon="Download" @click="exportExcel">导出 Excel</el-button>
    </div>

    <!-- ========== 1. 销售日报月报 ========== -->
    <div v-show="reportType === 'daily'">
      <!-- 汇总统计卡片 -->
      <div class="stat-grid" v-loading="loading">
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--brand)"><el-icon :size="20"><Money /></el-icon></div>
          <div>
            <div class="stat-label">销售额</div>
            <div class="stat-value num">¥ {{ daily.summary.sales.toFixed(2) }}</div>
            <div class="stat-trend">所选区间累计</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--info)"><el-icon :size="20"><Tickets /></el-icon></div>
          <div>
            <div class="stat-label">订单数</div>
            <div class="stat-value num">{{ daily.summary.orders }}</div>
            <div class="stat-trend">已结算订单</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--accent)"><el-icon :size="20"><Wallet /></el-icon></div>
          <div>
            <div class="stat-label">客单价</div>
            <div class="stat-value num">¥ {{ daily.summary.avg_price.toFixed(2) }}</div>
            <div class="stat-trend">销售额 / 订单数</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--success)"><el-icon :size="20"><ScaleToOriginal /></el-icon></div>
          <div>
            <div class="stat-label">称重重量</div>
            <div class="stat-value num">{{ daily.summary.weight_kg }} kg</div>
            <div class="stat-trend">称重商品合计</div>
          </div>
        </div>
      </div>
      <!-- 按日/按周销售柱状图 -->
      <div class="card chart-card">
        <div class="card-head">
          <h3>销售趋势</h3>
          <el-radio-group v-model="dailyMode" size="small">
            <el-radio-button value="day">按日</el-radio-button>
            <el-radio-button value="week">按周</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="dailyChartRef" class="chart-box"></div>
      </div>
    </div>

    <!-- ========== 2. 商品销售排行 ========== -->
    <div v-show="reportType === 'rank'">
      <div class="chart-row">
        <div class="card chart-card span-2">
          <div class="card-head">
            <h3>商品销售排行</h3>
            <span class="count-hint">Top 15</span>
          </div>
          <el-table :data="rankData" size="small" empty-text="暂无排行数据">
            <el-table-column label="排名" width="70" align="center">
              <template #default="{ $index }">
                <span class="rank-badge" :class="'rank-' + ($index + 1)">{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="商品" min-width="140" />
            <el-table-column prop="category" label="分类" width="90" align="center" />
            <el-table-column label="销量" width="110" align="right">
              <template #default="{ row }"><span class="num">{{ qtyText(row) }}</span></template>
            </el-table-column>
            <el-table-column label="销售额" width="110" align="right">
              <template #default="{ row }"><span class="num">¥{{ row.amount.toFixed(2) }}</span></template>
            </el-table-column>
            <el-table-column label="占比" min-width="170">
              <template #default="{ row }">
                <div class="ratio-cell">
                  <el-progress :percentage="row.ratio" :stroke-width="8" :color="ratioColor(row.ratio)" />
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="card chart-card">
          <div class="card-head">
            <h3>Top 10 销售额</h3>
          </div>
          <div ref="rankChartRef" class="chart-box"></div>
        </div>
      </div>
    </div>

    <!-- ========== 3. 时段分析 ========== -->
    <div v-show="reportType === 'hourly'">
      <div class="card chart-card">
        <div class="card-head">
          <h3>分时段销售额曲线（全天 24 小时）</h3>
          <el-tag v-if="hourly.total_sales > 0" type="warning" effect="light" size="small">高峰 {{ hourly.peak_label }}</el-tag>
        </div>
        <div ref="hourlyChartRef" class="chart-box tall"></div>
      </div>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">早高峰（8:00-11:00）</div>
          <div class="stat-value num">¥ {{ hourly.morning_sales.toFixed(2) }}</div>
          <div class="stat-trend">占全天 {{ pct(hourly.morning_sales) }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">午间（11:00-15:00）</div>
          <div class="stat-value num">¥ {{ hourly.noon_sales.toFixed(2) }}</div>
          <div class="stat-trend">占全天 {{ pct(hourly.noon_sales) }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">晚高峰（15:00-21:00）</div>
          <div class="stat-value num">¥ {{ hourly.evening_sales.toFixed(2) }}</div>
          <div class="stat-trend up">占全天 {{ pct(hourly.evening_sales) }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">全天销售额</div>
          <div class="stat-value num">¥ {{ hourly.total_sales.toFixed(2) }}</div>
          <div class="stat-trend">24 个时段</div>
        </div>
      </div>
    </div>

    <!-- ========== 4. 毛利分析 ========== -->
    <div v-show="reportType === 'profit'">
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--brand)"><el-icon :size="20"><Money /></el-icon></div>
          <div>
            <div class="stat-label">销售额</div>
            <div class="stat-value num">¥ {{ profit.sales.toFixed(2) }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--info)"><el-icon :size="20"><Box /></el-icon></div>
          <div>
            <div class="stat-label">成本</div>
            <div class="stat-value num">¥ {{ profit.cost.toFixed(2) }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--accent)"><el-icon :size="20"><TrendCharts /></el-icon></div>
          <div>
            <div class="stat-label">毛利</div>
            <div class="stat-value num">¥ {{ profit.profit.toFixed(2) }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--success)"><el-icon :size="20"><PieChart /></el-icon></div>
          <div>
            <div class="stat-label">毛利率</div>
            <div class="stat-value num">{{ profit.rate }}%</div>
          </div>
        </div>
      </div>
      <div class="card chart-card">
        <div class="card-head">
          <h3>分类毛利分析</h3>
          <span class="count-hint">销售额 / 毛利</span>
        </div>
        <div ref="profitChartRef" class="chart-box tall"></div>
      </div>
    </div>

    <!-- ========== 5. 会员分析 ========== -->
    <div v-show="reportType === 'member'">
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--brand)"><el-icon :size="20"><Avatar /></el-icon></div>
          <div>
            <div class="stat-label">会员总数</div>
            <div class="stat-value num">{{ memberReport.member_total }}</div>
            <div class="stat-trend up">区间新增 {{ memberReport.new_in_range }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--accent)"><el-icon :size="20"><Money /></el-icon></div>
          <div>
            <div class="stat-label">会员消费额</div>
            <div class="stat-value num">¥ {{ memberReport.member_sales.toFixed(2) }}</div>
            <div class="stat-trend">占销售 {{ memberReport.member_ratio }}%</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--info)"><el-icon :size="20"><Tickets /></el-icon></div>
          <div>
            <div class="stat-label">会员消费笔数</div>
            <div class="stat-value num">{{ memberReport.member_orders }}</div>
            <div class="stat-trend">会员订单合计</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="--c: var(--success)"><el-icon :size="20"><Star /></el-icon></div>
          <div>
            <div class="stat-label">会员复购率</div>
            <div class="stat-value num">{{ memberReport.repurchase_rate }}%</div>
            <div class="stat-trend">消费 2 笔及以上</div>
          </div>
        </div>
      </div>
      <div class="card chart-card">
        <div class="card-head">
          <h3>会员消费排行</h3>
          <span class="count-hint">Top 10</span>
        </div>
        <el-table :data="memberRank" size="small" empty-text="暂无会员消费数据">
          <el-table-column label="排名" width="70" align="center">
            <template #default="{ $index }">
              <span class="rank-badge" :class="'rank-' + ($index + 1)">{{ $index + 1 }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="会员" min-width="120" />
          <el-table-column prop="level" label="等级" width="90" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="levelTagType(row.level)" effect="light">{{ levelText(row.level) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="消费笔数" width="100" align="center">
            <template #default="{ row }"><span class="num">{{ row.orders }}</span></template>
          </el-table-column>
          <el-table-column label="消费金额" min-width="140" align="right">
            <template #default="{ row }"><span class="num">¥{{ row.amount.toFixed(2) }}</span></template>
          </el-table-column>
          <el-table-column label="消费占比" min-width="170">
            <template #default="{ row }">
              <el-progress :percentage="row.ratio" :stroke-width="8" :color="ratioColor(row.ratio)" />
            </template>
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
import { Download, Money, Tickets, Wallet, ScaleToOriginal, Box, TrendCharts, PieChart, Avatar, Star } from '@element-plus/icons-vue'
import {
  fetchDailyReport,
  fetchHourlyReport,
  fetchMemberReport,
  fetchProductRank,
  fetchProfitReport,
} from '../api'

/**
 * 生成默认日期区间：本月 1 日至今天
 * @returns {string[]} [开始日期, 结束日期]
 */
function defaultRange() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return [`${y}-${m}-01`, `${y}-${m}-${d}`]
}

// 日期范围与报表类型
const dateRange = ref(defaultRange())
const reportType = ref('daily')
// 销售日报月报：按日 / 按周
const dailyMode = ref('day')
// 报表加载态
const loading = ref(false)

// 图表容器引用
const dailyChartRef = ref(null)
const rankChartRef = ref(null)
const hourlyChartRef = ref(null)
const profitChartRef = ref(null)

// 主题色：品牌绿 / 暖橙 / 蓝 / 红
const COLORS = { green: '#2F9E5F', orange: '#F5A623', blue: '#4A90D9', red: '#E05B4D' }

/* ---------------- 报表数据 ---------------- */

// 销售日报月报数据
const daily = ref({
  summary: { sales: 0, orders: 0, avg_price: 0, weight_kg: 0 },
  trend: [],
})
// 商品排行数据
const rankData = ref([])
// 时段分析数据
const hourly = ref({
  total_sales: 0,
  peak_label: '',
  peak_sales: 0,
  morning_sales: 0,
  noon_sales: 0,
  evening_sales: 0,
  points: [],
})
// 毛利分析数据
const profit = ref({ sales: 0, cost: 0, profit: 0, rate: 0, categories: [] })
// 会员分析数据
const memberReport = ref({
  member_total: 0,
  new_in_range: 0,
  member_sales: 0,
  member_orders: 0,
  member_ratio: 0,
  repurchase_rate: 0,
  items: [],
})

// 会员消费排行
const memberRank = computed(() => memberReport.value.items)

// 会员等级：后端值 → 中文文案
const LEVEL_TO_TEXT = { normal: '普通卡', silver: '银卡', gold: '金卡' }

/**
 * 会员等级转中文
 * @param {string} level 后端等级值
 * @returns {string} 中文等级
 */
const levelText = (level) => LEVEL_TO_TEXT[level] || level || '普通卡'

/**
 * 会员等级对应标签颜色
 * @param {string} level 后端等级值
 * @returns {string} el-tag 类型
 */
const levelTagType = (level) => (level === 'gold' ? 'warning' : level === 'silver' ? 'info' : 'primary')

/**
 * 商品销量展示文案（称重商品显示 kg，按件商品显示单位）
 * @param {object} row 排行行
 * @returns {string} 销量文案
 */
function qtyText(row) {
  return `${row.qty}${row.is_weighted ? ' kg' : ` ${row.unit}`}`
}

// 占比进度条颜色：占比 50% 以上橙色，其余品牌绿
const ratioColor = (ratio) => (ratio >= 50 ? COLORS.orange : COLORS.green)

/**
 * 某时段销售额占全天比例
 * @param {number} value 时段销售额
 * @returns {string} 百分比文案
 */
const pct = (value) =>
  hourly.value.total_sales ? ((value / hourly.value.total_sales) * 100).toFixed(1) : '0.0'

/**
 * 加载当前日期区间的全部报表数据
 * @returns {Promise<void>}
 */
async function loadReports() {
  if (!dateRange.value || dateRange.value.length < 2) return
  const [start, end] = dateRange.value
  loading.value = true
  try {
    const [d, r, h, p, m] = await Promise.all([
      fetchDailyReport({ start, end, mode: dailyMode.value }),
      fetchProductRank({ start, end }),
      fetchHourlyReport({ start, end }),
      fetchProfitReport({ start, end }),
      fetchMemberReport({ start, end }),
    ])
    daily.value = d
    rankData.value = r.items || []
    hourly.value = h
    profit.value = p
    memberReport.value = m
    await nextTick()
    renderActiveChart()
  } catch (err) {
    ElMessage.error(`报表加载失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

/**
 * 取得或创建图表实例（避免重复初始化告警）
 * @param {HTMLElement} el 图表容器
 * @returns {object} ECharts 实例
 */
const getChart = (el) => echarts.getInstanceByDom(el) || echarts.init(el)

/**
 * 渲染当前报表类型对应的图表
 */
function renderActiveChart() {
  if (reportType.value === 'daily') initDailyChart()
  if (reportType.value === 'rank') initRankChart()
  if (reportType.value === 'hourly') initHourlyChart()
  if (reportType.value === 'profit') initProfitChart()
}

// 切换报表类型时等 DOM 可见后重绘
watch(reportType, () => nextTick(renderActiveChart))

// 日期或按日/按周变化时重新请求
watch([dateRange, dailyMode], loadReports)

onMounted(loadReports)

// 销售趋势柱状图（按日 / 按周）
const initDailyChart = () => {
  if (!dailyChartRef.value) return
  const chart = getChart(dailyChartRef.value)
  const isDay = dailyMode.value === 'day'
  const trend = daily.value.trend || []
  chart.setOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: trend.map((t) => t.label),
        axisLine: { lineStyle: { color: '#c9c9c9' } },
        axisLabel: { color: '#8a8a8a' },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f0f0f0' } },
        axisLabel: { color: '#8a8a8a', formatter: '{value}' },
      },
      series: [
        {
          name: '销售额(元)',
          type: 'bar',
          barWidth: isDay ? 22 : 48,
          data: trend.map((t) => t.sales),
          itemStyle: { color: COLORS.green, borderRadius: [4, 4, 0, 0] },
        },
      ],
    },
    true,
  )
  chart.resize()
}

// 商品销售排行 Top10 横向条形图
const initRankChart = () => {
  if (!rankChartRef.value) return
  const chart = getChart(rankChartRef.value)
  const top10 = rankData.value.slice(0, 10).slice().reverse()
  chart.setOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 8, right: 40, top: 10, bottom: 10, containLabel: true },
      xAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f0f0f0' } },
        axisLabel: { color: '#8a8a8a' },
      },
      yAxis: {
        type: 'category',
        data: top10.map((r) => r.name),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#555' },
      },
      series: [
        {
          name: '销售额',
          type: 'bar',
          barWidth: 14,
          data: top10.map((r) => r.amount),
          itemStyle: { color: COLORS.green, borderRadius: [0, 4, 4, 0] },
        },
      ],
    },
    true,
  )
  chart.resize()
}

// 时段分析折线图（全天 24 小时，含高峰标注）
const initHourlyChart = () => {
  if (!hourlyChartRef.value) return
  const chart = getChart(hourlyChartRef.value)
  // 展示完整 24 小时，避免营业时间外产生的订单销售额在图表中不可见
  const points = hourly.value.points || []
  const labels = points.map((p) => p.label)
  const data = points.map((p) => p.sales)
  const maxIndex = data.indexOf(Math.max(...(data.length ? data : [0])))
  const markPoint =
    data.length && data[maxIndex] > 0
      ? {
          symbolSize: 46,
          label: { color: '#fff', fontSize: 11, formatter: '高峰' },
          data: [{ coord: [labels[maxIndex], data[maxIndex]], value: data[maxIndex], itemStyle: { color: COLORS.red } }],
        }
      : undefined
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 30, top: 40, bottom: 30 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: labels,
        axisLine: { lineStyle: { color: '#c9c9c9' } },
        axisLabel: { color: '#8a8a8a' },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f0f0f0' } },
        axisLabel: { color: '#8a8a8a' },
      },
      series: [
        {
          name: '销售额(元)',
          type: 'line',
          smooth: true,
          data,
          itemStyle: { color: COLORS.orange },
          lineStyle: { width: 3 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(245,166,35,0.28)' },
                { offset: 1, color: 'rgba(245,166,35,0.02)' },
              ],
            },
          },
          markPoint,
        },
      ],
    },
    true,
  )
  chart.resize()
}

// 毛利分析柱状图（销售额 + 毛利双柱）
const initProfitChart = () => {
  if (!profitChartRef.value) return
  const chart = getChart(profitChartRef.value)
  const categories = (profit.value.categories || []).map((c) => c.category)
  const sales = (profit.value.categories || []).map((c) => c.sales)
  const profits = (profit.value.categories || []).map((c) => c.profit)
  chart.setOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { top: 0, icon: 'circle', itemWidth: 8, textStyle: { color: '#555' } },
      grid: { left: 50, right: 20, top: 40, bottom: 30 },
      xAxis: {
        type: 'category',
        data: categories,
        axisLine: { lineStyle: { color: '#c9c9c9' } },
        axisLabel: { color: '#8a8a8a' },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f0f0f0' } },
        axisLabel: { color: '#8a8a8a' },
      },
      series: [
        {
          name: '销售额',
          type: 'bar',
          barWidth: 22,
          data: sales,
          itemStyle: { color: COLORS.blue, borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '毛利',
          type: 'bar',
          barWidth: 22,
          data: profits,
          itemStyle: { color: COLORS.green, borderRadius: [4, 4, 0, 0] },
        },
      ],
    },
    true,
  )
  chart.resize()
}

/**
 * 转义 CSV 单元格内容
 * @param {*} value 单元格值
 * @returns {string} 转义后的文本
 */
function csvCell(value) {
  const text = String(value ?? '')
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

/**
 * 导出当前报表为 CSV（Excel 可直接打开）
 */
function exportExcel() {
  let header = []
  let rows = []
  if (reportType.value === 'daily') {
    header = ['日期/周', '销售额', '订单数']
    rows = daily.value.trend.map((t) => [t.label, t.sales, t.orders])
  } else if (reportType.value === 'rank') {
    header = ['商品', '分类', '销量', '单位', '销售额', '占比%']
    rows = rankData.value.map((r) => [r.name, r.category, r.qty, r.unit, r.amount, r.ratio])
  } else if (reportType.value === 'hourly') {
    header = ['时段', '销售额', '订单数']
    rows = hourly.value.points.map((p) => [p.label, p.sales, p.orders])
  } else if (reportType.value === 'profit') {
    header = ['分类', '销售额', '成本', '毛利', '毛利率%']
    rows = profit.value.categories.map((c) => [c.category, c.sales, c.cost, c.profit, c.rate])
  } else {
    header = ['会员', '等级', '消费笔数', '消费金额', '占比%']
    rows = memberRank.value.map((m) => [m.name, levelText(m.level), m.orders, m.amount, m.ratio])
  }
  const csv = [header, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n')
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `报表_${reportType.value}_${(dateRange.value || []).join('_')}.csv`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('报表已导出（CSV，可用 Excel 打开）')
}
</script>

<style scoped>
.reports {
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
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
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
  width: 44px;
  height: 44px;
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
  font-size: 22px;
  font-weight: 700;
  color: var(--neutral-900);
  line-height: 1.3;
}
.stat-trend {
  font-size: 12px;
  color: var(--neutral-400);
}
.stat-trend.up {
  color: var(--success);
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
.count-hint {
  font-size: 12px;
  color: var(--neutral-400);
}
.chart-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.chart-card {
  margin-bottom: 16px;
}
.chart-card.span-2 {
  grid-column: span 2;
}
.chart-box {
  height: 280px;
}
.chart-box.tall {
  height: 320px;
}
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--neutral-100);
  color: var(--neutral-500);
  font-size: 12px;
  font-weight: 600;
}
.rank-badge.rank-1 {
  background: #F5A623;
  color: #fff;
}
.rank-badge.rank-2 {
  background: #8a8a8a;
  color: #fff;
}
.rank-badge.rank-3 {
  background: #b56a3c;
  color: #fff;
}
.ratio-cell {
  padding-right: 12px;
}
</style>
