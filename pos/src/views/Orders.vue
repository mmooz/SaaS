<template>
  <div class="orders-page">
    <!-- 可见范围：由服务端 scope 决定，前端仅展示不做权限判断 -->
    <div class="scope-banner" :class="scope === 'all' ? 'all' : 'own'">
      <span class="scope-dot" />
      <span class="scope-text">{{ scopeText }}</span>
      <span class="scope-user">{{ cashierLabel }}</span>
    </div>

    <!-- 筛选工具栏 -->
    <div class="toolbar-card">
      <div class="filters">
        <el-input
          v-model="filters.keyword"
          placeholder="订单号 / 会员手机号"
          clearable
          class="filter-keyword"
          @keyup.enter="search"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          class="filter-date"
        />
        <el-select v-model="filters.status" placeholder="订单状态" clearable class="filter-status">
          <el-option label="待支付" value="pending" />
          <el-option label="已支付" value="paid" />
          <el-option label="部分退款" value="partially_refunded" />
          <el-option label="已退款" value="refunded" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查 询</el-button>
        <el-button :icon="Refresh" @click="reset">重 置</el-button>
      </div>
    </div>

    <!-- 本机待上传订单提示：离线结算的单也会计入本账号产生的订单 -->
    <div v-if="localOrders.length" class="local-tip">
      本机还有 {{ localOrders.length }} 笔离线订单待上传，已在下方列表以「待上传」标出；联网补传后自动并入服务端记录。
    </div>

    <!-- 订单列表 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="rows"
        class="order-table"
        empty-text="当前账号暂无订单；新结算的订单会自动归属到本账号（历史无归属订单仅管理员可见）"
      >
        <el-table-column label="订单号" min-width="210">
          <template #default="{ row }">
            <span class="num order-no">{{ row.order_no }}</span>
            <el-tag v-if="row.isLocal" type="warning" size="small" class="local-tag">待上传</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" min-width="160">
          <template #default="{ row }"><span class="num">{{ formatTime(row.created_at) }}</span></template>
        </el-table-column>
        <el-table-column label="收银员" min-width="110">
          <template #default="{ row }">{{ row.cashier_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="金额" min-width="120" align="right">
          <template #default="{ row }"><span class="num amount">¥{{ money(row.total_amount) }}</span></template>
        </el-table-column>
        <el-table-column label="优惠" min-width="100" align="right">
          <template #default="{ row }"><span class="num">¥{{ money(row.discount_amount) }}</span></template>
        </el-table-column>
        <el-table-column label="已退款" min-width="100" align="right">
          <template #default="{ row }"><span class="num">¥{{ money(row.refunded_amount) }}</span></template>
        </el-table-column>
        <el-table-column label="支付方式" min-width="110">
          <template #default="{ row }">{{ payText(row) }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }">
            <el-tag v-if="row.isLocal" type="warning" size="small">待上传</el-tag>
            <el-tag v-else :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="pageSize"
          @current-change="loadOrders"
        />
      </div>
    </div>

    <!-- 订单详情抽屉 -->
    <el-drawer v-model="detailVisible" title="订单详情" size="480px">
      <template v-if="detail">
        <section class="detail-head">
          <div class="detail-no num">{{ detail.order_no }}</div>
          <div class="detail-meta">
            {{ formatTime(detail.created_at) }} · {{ detail.cashier_name || '—' }}
            · <el-tag :type="detail.isLocal ? 'warning' : statusType(detail.status)" size="small">
              {{ detail.isLocal ? '待上传' : statusText(detail.status) }}
            </el-tag>
          </div>
          <div v-if="detail.member_mobile" class="detail-meta">会员手机号：{{ detail.member_mobile }}</div>
          <div v-if="detail.remark" class="detail-meta">备注：{{ detail.remark }}</div>
        </section>

        <section class="detail-summary">
          <div><span>商品合计</span><span class="num">¥{{ money(itemsTotal) }}</span></div>
          <div><span>优惠</span><span class="num">- ¥{{ money(detail.discount_amount) }}</span></div>
          <div><span>已退款</span><span class="num">¥{{ money(detail.refunded_amount) }}</span></div>
          <div class="summary-total"><span>实收</span><span class="num">¥{{ money(detail.total_amount) }}</span></div>
          <div class="detail-pay">支付方式：{{ payText(detail) }}</div>
        </section>

        <div class="detail-section-title">商品明细（{{ (detail.items || []).length }}）</div>
        <div v-for="(item, i) in detail.items || []" :key="i" class="detail-item">
          <div class="item-main">
            <span class="item-name">{{ item.name }}</span>
            <el-tag v-if="item.refunded" type="danger" size="small">已退货</el-tag>
          </div>
          <div class="item-sub num">
            {{ item.is_weighted ? `${Number(item.weight_kg || 0).toFixed(3)}kg` : `×${item.qty}` }}
            × ¥{{ money(item.unit_price) }}
          </div>
          <div class="num item-amount">¥{{ money(item.amount) }}</div>
        </div>
        <div v-if="!(detail.items || []).length" class="empty-tip">该订单无商品明细</div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { fetchOrders } from '../api'
import { usePosStore } from '../stores/posStore'
import { OrderPrintMapper } from '../services/print/OrderPrintMapper'
import { PrintFormatter as F } from '../services/print/PrintFormatter'

const store = usePosStore()
const loading = ref(false)
const orders = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
// 服务端返回的可见范围：own=仅本人 / all=全店；前端仅用于文案，不做权限判断
const scope = ref('')
const filters = reactive({ keyword: '', dateRange: [], status: '' })
const detailVisible = ref(false)
const detail = ref(null)

const cashierLabel = computed(() => {
  const u = store.cashier
  return u ? `${u.name || u.username}${u.role === 'cashier' ? '（收银员）' : '（管理员）'}` : '未登录'
})
const isManagerLocal = computed(() => ['admin', 'manager', 'super'].includes(store.cashier?.role))
const scopeText = computed(() => {
  if (scope.value === 'own') return '收银员视图：仅显示当前账号产生的订单'
  if (scope.value === 'all') return '管理员视图：可查询本店全部订单'
  return isManagerLocal.value
    ? '管理员视图：可查询本店全部订单'
    : '收银员视图：仅显示当前账号产生的订单'
})

// 本机离线队列镜像：断网时结算的单同样是本账号产生的订单
const localOrders = computed(() =>
  (store.offlineOrders || []).map((o) => ({
    ...o,
    isLocal: true,
    cashier_name: store.cashier?.name || '',
    refunded_amount: 0,
  })),
)
const rows = computed(() => [...localOrders.value, ...orders.value])

/** 金额统一两位小数，空值按 0 处理 */
const money = (v) => Number(v || 0).toFixed(2)
/** 时间格式化，兼容服务端 naive UTC 与离线单 ISO 串 */
const formatTime = (v) => F.datetime(v)
/** 支付方式文案解析，异常时返回占位符 */
const payText = (o) => {
  try {
    return OrderPrintMapper.payMethod(o.pay_details) || '—'
  } catch {
    return '—'
  }
}
const statusText = (s) =>
  ({ pending: '待支付', paid: '已支付', refunded: '已退款', partially_refunded: '部分退款' }[s] || s || '—')
const statusType = (s) =>
  ({ pending: 'warning', paid: 'success', refunded: 'danger', partially_refunded: 'warning' }[s] || 'info')

/** 拉取订单列表；权限过滤在服务端完成，客户端不传角色参数 */
const loadOrders = async () => {
  loading.value = true
  try {
    const [start, end] = filters.dateRange || []
    const res = await fetchOrders({
      keyword: filters.keyword.trim() || undefined,
      status: filters.status || undefined,
      start: start ? `${start} 00:00:00` : undefined,
      end: end ? `${end} 23:59:59` : undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    orders.value = res.items || []
    total.value = Number(res.total || 0)
    scope.value = res.scope || ''
  } catch (err) {
    ElMessage.error(`订单加载失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

/** 按条件重新查询并回到第一页 */
const search = async () => {
  page.value = 1
  await loadOrders()
}

/** 清空筛选条件并刷新 */
const reset = async () => {
  filters.keyword = ''
  filters.dateRange = []
  filters.status = ''
  await search()
}

/** 打开订单详情（列表数据已含明细，无需二次请求） */
const showDetail = (row) => {
  detail.value = row
  detailVisible.value = true
}

const itemsTotal = computed(() =>
  (detail.value?.items || []).reduce((sum, i) => sum + Number(i.amount || 0), 0),
)

onMounted(async () => {
  // 直接打开本页（刷新）时也要能恢复离线订单队列镜像
  try {
    await store.initOffline()
  } catch (err) {
    console.error('[Orders] 恢复离线队列失败', err)
  }
  await loadOrders()
})
</script>

<style scoped>
.orders-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ----- 可见范围横幅（与管理页信息条风格一致） ----- */
.scope-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  background: var(--neutral-50);
  font-size: 14px;
  color: var(--neutral-700);
}
.scope-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--brand);
}
.scope-banner.all .scope-dot {
  background: var(--accent);
}
.scope-user {
  margin-left: auto;
  color: var(--neutral-500);
}

/* ----- 筛选工具栏（与管理页 toolbar-card 一致） ----- */
.toolbar-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-keyword {
  width: 260px;
}
.filter-date {
  width: 280px;
}
.filter-status {
  width: 150px;
}
.local-tip {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  color: var(--neutral-600);
  font-size: 14px;
  line-height: 1.6;
}

/* ----- 表格卡片（与管理页 table-card 一致） ----- */
.table-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 6px 18px 16px;
}
.order-table :deep(.el-table__row) {
  font-size: 14px;
}
.order-table :deep(th.el-table__cell) {
  font-size: 14px;
  background: var(--neutral-50);
  color: var(--neutral-600);
}
.order-no {
  font-size: 14px;
  color: var(--neutral-700);
  word-break: break-all;
}
.local-tag {
  margin-left: 6px;
}
.amount {
  font-weight: 700;
  color: var(--danger);
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

/* ----- 详情抽屉 ----- */
.detail-head {
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--neutral-200);
}
.detail-no {
  font-size: 17px;
  font-weight: 700;
  word-break: break-all;
}
.detail-meta {
  margin-top: 8px;
  font-size: 14px;
  color: var(--neutral-500);
}
.detail-summary {
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--neutral-200);
}
.detail-summary > div {
  display: flex;
  justify-content: space-between;
  font-size: 15px;
  padding: 5px 0;
  color: var(--neutral-600);
}
.detail-summary .summary-total {
  font-size: 18px;
  font-weight: 700;
  color: var(--neutral-900);
  border-top: 1px dashed var(--neutral-200);
  margin-top: 6px;
  padding-top: 10px;
}
.detail-pay {
  font-size: 14px !important;
  justify-content: flex-start !important;
}
.detail-section-title {
  font-size: 16px;
  font-weight: 600;
  margin: var(--space-4) 0 var(--space-2);
}
.detail-item {
  position: relative;
  padding: 12px 14px;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  margin-bottom: 10px;
}
.item-main {
  display: flex;
  align-items: center;
  gap: 8px;
}
.item-name {
  font-size: 16px;
  font-weight: 600;
}
.item-sub {
  font-size: 13px;
  color: var(--neutral-400);
  margin-top: 4px;
}
.item-amount {
  position: absolute;
  right: 14px;
  top: 18px;
  font-size: 17px;
  font-weight: 700;
}
.empty-tip {
  text-align: center;
  padding: var(--space-5) 0;
  color: var(--neutral-400);
}
</style>
