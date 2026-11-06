<!-- 交接班页面：班次列表、班次汇总与交接明细 -->
<template>
  <div class="shift-page">
    <!-- 筛选工具栏 -->
    <div class="filters">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        class="filter-date"
      />
      <el-select v-model="status" placeholder="班次状态" clearable class="filter-status">
        <el-option label="进行中" value="open" />
        <el-option label="已交班" value="closed" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
    </div>

    <!-- 班次列表 -->
    <el-table :data="shifts" v-loading="loading" stripe empty-text="暂无班次数据">
      <el-table-column label="收银员" min-width="130">
        <template #default="{ row }">{{ cashierName(row.cashier_id) }}</template>
      </el-table-column>
      <el-table-column label="开班时间" min-width="160">
        <template #default="{ row }">{{ formatTime(row.start_at) }}</template>
      </el-table-column>
      <el-table-column label="交班时间" min-width="160">
        <template #default="{ row }">{{ row.end_at ? formatTime(row.end_at) : '进行中' }}</template>
      </el-table-column>
      <el-table-column label="底金" width="100" align="right">
        <template #default="{ row }">￥{{ money(row.base_cash) }}</template>
      </el-table-column>
      <el-table-column label="销售额" width="110" align="right">
        <template #default="{ row }">￥{{ money(row.total_sales) }}</template>
      </el-table-column>
      <el-table-column prop="order_count" label="订单数" width="90" align="right" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'open' ? 'warning' : 'success'" effect="light">
            {{ row.status === 'open' ? '进行中' : '已交班' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openSummary(row)">交接明细</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadShifts"
        @size-change="search"
      />
    </div>

    <!-- 班次汇总弹窗 -->
    <el-dialog v-model="summaryVisible" title="班次交接明细" width="620px" destroy-on-close>
      <div v-if="summary" class="summary-body">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="收银员">{{ cashierName(summary.shift.cashier_id) }}</el-descriptions-item>
          <el-descriptions-item label="班次状态">
            {{ summary.shift.status === 'open' ? '进行中' : '已交班' }}
          </el-descriptions-item>
          <el-descriptions-item label="开班时间">{{ formatTime(summary.shift.start_at) }}</el-descriptions-item>
          <el-descriptions-item label="交班时间">
            {{ summary.shift.end_at ? formatTime(summary.shift.end_at) : '未交班' }}
          </el-descriptions-item>
          <el-descriptions-item label="订单数">{{ summary.order_count }}</el-descriptions-item>
          <el-descriptions-item label="销售额">￥{{ money(summary.total_sales) }}</el-descriptions-item>
          <el-descriptions-item label="退款金额">￥{{ money(summary.refund_amount) }}</el-descriptions-item>
          <el-descriptions-item label="现金底金">￥{{ money(summary.shift.base_cash) }}</el-descriptions-item>
          <el-descriptions-item label="现金应交">￥{{ money(summary.cash_should) }}</el-descriptions-item>
          <el-descriptions-item label="实际点钞">
            {{ summary.actual_cash == null ? '未填写' : `￥${money(summary.actual_cash)}` }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="summary-section">
          <h4>支付方式汇总</h4>
          <el-table :data="summary.payments" size="small" border empty-text="暂无支付数据">
            <el-table-column prop="method" label="支付方式" min-width="120" />
            <el-table-column label="金额" width="110" align="right">
              <template #default="{ row }">￥{{ money(row.amount) }}</template>
            </el-table-column>
            <el-table-column prop="count" label="笔数" width="90" align="right" />
          </el-table>
        </div>
      </div>
      <div v-else v-loading="summaryLoading" class="summary-loading" />
      <template #footer>
        <el-button @click="summaryVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { fetchShiftSummary, fetchShifts, fetchUsers } from '../api'

// 班次列表数据
const shifts = ref([])
// 列表加载状态
const loading = ref(false)
// 总记录数
const total = ref(0)
// 当前页码
const page = ref(1)
// 每页条数
const pageSize = ref(20)
// 日期范围筛选
const dateRange = ref([])
// 班次状态筛选
const status = ref('')

// 用户 ID -> 姓名字典（用于展示收银员）
const userNames = ref({})

// 汇总弹窗可见状态
const summaryVisible = ref(false)
// 当前班次汇总数据
const summary = ref(null)
// 汇总加载状态
const summaryLoading = ref(false)

/**
 * 把接口时间转成便于阅读的本地时间
 * @param {string} value ISO 时间字符串
 * @returns {string} 格式化时间
 */
function formatTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

/**
 * 金额格式化（保留两位小数）
 * @param {number} value 金额
 * @returns {string} 金额文本
 */
function money(value) {
  return Number(value || 0).toFixed(2)
}

/**
 * 按用户 ID 展示收银员姓名
 * @param {number|string} cashierId 收银员 ID
 * @returns {string} 收银员姓名或 ID
 */
function cashierName(cashierId) {
  return userNames.value[cashierId] || `#${cashierId}`
}

/**
 * 加载本租户员工，建立 ID -> 姓名映射
 * @returns {Promise<void>}
 */
async function loadUsers() {
  try {
    const res = await fetchUsers({ pageSize: 100 })
    const map = {}
    for (const user of res.items || []) {
      map[user.id] = user.name || user.username
    }
    userNames.value = map
  } catch {
    // 员工列表加载失败不阻断班次列表展示，姓名处回退显示 ID
  }
}

/**
 * 组装时间范围参数：结束日期按当天 23:59:59 处理
 * @returns {{ start?: string, end?: string }} 时间参数
 */
function timeParams() {
  const [start, end] = dateRange.value || []
  return {
    start: start ? `${start} 00:00:00` : undefined,
    end: end ? `${end} 23:59:59` : undefined,
  }
}

/**
 * 加载班次列表
 * @returns {Promise<void>}
 */
async function loadShifts() {
  loading.value = true
  try {
    const res = await fetchShifts({
      status: status.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
      ...timeParams(),
    })
    shifts.value = res.items || []
    total.value = res.total || 0
  } catch (err) {
    ElMessage.error(`加载班次失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

/**
 * 按当前筛选条件重新查询（回到第一页）
 * @returns {Promise<void>}
 */
async function search() {
  page.value = 1
  await loadShifts()
}

/**
 * 重置筛选条件并重新查询
 * @returns {Promise<void>}
 */
async function resetFilters() {
  dateRange.value = []
  status.value = ''
  await search()
}

/**
 * 打开班次汇总弹窗
 * @param {object} row 班次行数据
 * @returns {Promise<void>}
 */
async function openSummary(row) {
  summary.value = null
  summaryVisible.value = true
  summaryLoading.value = true
  try {
    summary.value = await fetchShiftSummary(row.id)
  } catch (err) {
    ElMessage.error(`加载班次汇总失败：${err.message}`)
  } finally {
    summaryLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadShifts()])
})
</script>

<style scoped>
.shift-page {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  box-shadow: var(--shadow-sm);
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}
.filter-date {
  width: 260px;
}
.filter-status {
  width: 140px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.summary-section {
  margin-top: 18px;
}
.summary-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--neutral-700);
}
.summary-loading {
  height: 160px;
}
</style>
