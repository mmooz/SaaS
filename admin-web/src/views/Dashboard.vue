<template>
  <div class="dashboard">
    <!-- 顶部统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon" style="--c: var(--brand)"><el-icon :size="22"><Money /></el-icon></div>
        <div>
          <div class="stat-label">今日销售额</div>
          <div class="stat-value num">¥ 12,684.50</div>
          <div class="stat-trend up">较昨日 +8.2%</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="--c: var(--info)"><el-icon :size="22"><Tickets /></el-icon></div>
        <div>
          <div class="stat-label">今日订单数</div>
          <div class="stat-value num">236</div>
          <div class="stat-trend up">较昨日 +12</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="--c: var(--accent)"><el-icon :size="22"><ScaleToOriginal /></el-icon></div>
        <div>
          <div class="stat-label">今日称重单数</div>
          <div class="stat-value num">178</div>
          <div class="stat-trend">占比 75.4%</div>
        </div>
      </div>
      <div class="stat-card warn">
        <div class="stat-icon" style="--c: var(--danger)"><el-icon :size="22"><Warning /></el-icon></div>
        <div>
          <div class="stat-label">低库存预警</div>
          <div class="stat-value num">6</div>
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
          <div v-for="w in warnings" :key="w.name" class="warn-item">
            <div class="warn-info">
              <span class="warn-name">{{ w.name }}</span>
              <span class="warn-amount num">剩 {{ w.stock }}{{ w.unit }} / 安全 {{ w.safety }}</span>
            </div>
            <el-tag size="small" type="danger" effect="light">库存不足</el-tag>
          </div>
        </div>
      </div>
      <div class="chart-card span-2">
        <div class="card-head">
          <h3>最近订单</h3>
          <el-button link type="primary" size="small">查看全部 →</el-button>
        </div>
        <el-table :data="recentOrders" size="small" class="order-table">
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
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { Money, Tickets, ScaleToOriginal, Warning } from '@element-plus/icons-vue'

const trendRef = ref(null)
const cateRef = ref(null)
const trendRange = ref('7')

// 模拟数据：低库存预警列表
const warnings = [
  { name: '上海青', stock: '2.4', safety: '10', unit: 'kg' },
  { name: '西红柿', stock: '5.0', safety: '15', unit: 'kg' },
  { name: '鲜鸡蛋(盒)', stock: '8', safety: '30', unit: '盒' },
  { name: '土豆', stock: '12', safety: '40', unit: 'kg' },
  { name: '蜜桔', stock: '6.5', safety: '20', unit: 'kg' },
  { name: '五花肉', stock: '3.2', safety: '8', unit: 'kg' },
]

// 模拟数据：最近订单
const recentOrders = [
  { orderNo: '20261105-0212', items: '上海青 ×0.86kg、五花肉 ×0.42kg', payMethod: '微信', amount: 18.68, time: '18:32' },
  { orderNo: '20261105-0211', items: '蜜桔 ×2.1kg、香蕉 ×1.2kg', payMethod: '现金', amount: 23.4, time: '18:25' },
  { orderNo: '20261105-0210', items: '鲜鸡蛋(盒) ×1、土豆 ×1.5kg', payMethod: '储值', amount: 21.9, time: '18:19' },
  { orderNo: '20261105-0209', items: '西红柿 ×1.8kg、黄瓜 ×1.4kg', payMethod: '支付宝', amount: 19.72, time: '18:11' },
  { orderNo: '20261105-0208', items: '前腿肉 ×0.6kg、大蒜 ×0.2kg', payMethod: '现金', amount: 22.16, time: '18:04' },
]

// 支付方式对应的标签类型
const payTagType = (m) => {
  if (m === '现金') return 'warning'
  if (m === '储值') return 'success'
  return 'primary'
}

onMounted(() => {
  // 销售趋势图：折线 + 面积
  const trend = echarts.init(trendRef.value)
  trend.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['10-30', '10-31', '11-01', '11-02', '11-03', '11-04', '11-05'],
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
        type: 'line',
        smooth: true,
        data: [9280, 10460, 11730, 10280, 13620, 11720, 12684],
        itemStyle: { color: '#2F9E5F' },
        lineStyle: { width: 3 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(47,158,95,0.25)' },
              { offset: 1, color: 'rgba(47,158,95,0.02)' },
            ],
          },
        },
      },
    ],
  })

  // 分类占比饼图
  const cate = echarts.init(cateRef.value)
  cate.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, textStyle: { color: '#555' } },
    series: [
      {
        name: '分类占比',
        type: 'pie',
        radius: ['42%', '70%'],
        center: ['50%', '45%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: [
          { value: 32, name: '蔬菜', itemStyle: { color: '#2F9E5F' } },
          { value: 24, name: '水果', itemStyle: { color: '#F5A623' } },
          { value: 18, name: '肉类', itemStyle: { color: '#E05B4D' } },
          { value: 12, name: '水产', itemStyle: { color: '#4A90D9' } },
          { value: 14, name: '粮油副食', itemStyle: { color: '#8A8F3B' } },
        ],
      },
    ],
  })
})
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
