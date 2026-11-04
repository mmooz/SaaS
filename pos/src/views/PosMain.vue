<template>
  <div class="pos-page">
    <!-- ===== 顶部栏 ===== -->
    <header class="pos-header">
      <div class="header-left">
        <div class="store-name">鲜果超市 · 1号收银台</div>
        <div class="header-meta">
          <span class="shift-chip">早班 · 08:00 接班</span>
          <span class="sync-chip ok">已同步</span>
        </div>
      </div>
      <div class="header-clock num">{{ now }}</div>
      <div class="header-actions">
        <el-button size="large" @click="$router.push('/reprint')"><el-icon><Printer /></el-icon>&nbsp;补打</el-button>
        <el-button size="large" @click="$router.push('/refund')"><el-icon><RefreshLeft /></el-icon>&nbsp;退款</el-button>
        <el-button size="large" @click="$router.push('/shift')"><el-icon><Switch /></el-icon>&nbsp;交接班</el-button>
        <el-button size="large" @click="$router.push('/settings')"><el-icon><Setting /></el-icon></el-button>
      </div>
    </header>

    <!-- ===== 主体三栏 ===== -->
    <div class="pos-body">
      <!-- 左栏：分类 + 商品 -->
      <aside class="col-products">
        <div class="search-bar">
          <el-input v-model="keyword" placeholder="扫码 / 商品名 / 拼音码" size="large" clearable>
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="category-tabs">
          <button
            v-for="c in categories"
            :key="c"
            class="cat-tab"
            :class="{ active: currentCate === c }"
            @click="currentCate = c"
          >{{ c }}</button>
        </div>
        <div class="product-grid">
          <button
            v-for="p in filteredProducts"
            :key="p.id"
            class="product-cell"
            :class="{ weighted: p.pricingMode === 'weigh' }"
            @click="addProduct(p)"
          >
            <div class="p-name">{{ p.name }}</div>
            <div class="p-price num">¥{{ p.price.toFixed(2) }}</div>
            <div class="p-unit">{{ p.unit }}</div>
            <div v-if="p.pricingMode === 'weigh'" class="p-badge">称重</div>
          </button>
        </div>
      </aside>

      <!-- 中栏：购物车 -->
      <section class="col-cart">
        <div class="cart-head">
          <span>购物车（{{ cart.length }} 项）</span>
          <el-button text @click="clearCart">清空</el-button>
        </div>
        <div class="cart-list">
          <div v-if="cart.length === 0" class="cart-empty">
            <div class="empty-icon">🛒</div>
            <p>请选择商品或放上秤盘</p>
          </div>
          <div v-for="item in cart" :key="item.productId + item.weightKey" class="cart-item">
            <div class="ci-main">
              <div class="ci-name">{{ item.name }}</div>
              <div class="ci-sub num">
                <template v-if="item.weighted">
                  {{ item.weight.toFixed(2) }} kg × ¥{{ item.price.toFixed(2) }}
                </template>
                <template v-else>× {{ item.qty }}</template>
              </div>
            </div>
            <div class="ci-right">
              <div class="ci-amount num">¥{{ item.amount.toFixed(2) }}</div>
              <div class="ci-ops">
                <button class="op-btn" @click="decItem(item)">−</button>
                <button class="op-btn" @click="incItem(item)">+</button>
                <button class="op-btn danger" @click="removeItem(item)">✕</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右栏：称重 + 结算 -->
      <aside class="col-settle">
        <div class="weight-card" :class="{ stable: scaleStable }">
          <div class="weight-label">
            {{ currentProduct ? `正在称重 · ${currentProduct.name}` : '电子秤' }}
          </div>
          <div class="weight-value num">{{ weightDisplay }}</div>
          <div class="weight-unit">{{ weightUnit }}</div>
          <div class="weight-state" :class="{ ok: scaleStable }">
            {{ scaleStable ? '● 重量已稳定' : '○ 等待稳定…' }}
          </div>
          <div class="scale-ops">
            <button class="scale-btn" @click="doTare">去皮</button>
            <button class="scale-btn" @click="doZero">置零</button>
          </div>
          <div class="scale-status" :class="{ online: scaleOnline }">
            {{ scaleOnline ? '秤连接正常' : '秤未连接' }}
            <span v-if="!scaleOnline" class="manual-link" @click="manualWeight = true">手动输入重量</span>
          </div>
        </div>

        <div class="total-card">
          <div class="total-row">
            <span>应收合计</span>
            <span class="total-value num">¥{{ totalAmount.toFixed(2) }}</span>
          </div>
          <div class="discount-row num" v-if="discount > 0">
            优惠 −¥{{ discount.toFixed(2) }}
          </div>
          <div class="pay-buttons">
            <button class="pay-btn" @click="openPay('现金')">💵 现金</button>
            <button class="pay-btn blue" @click="openPay('微信')">📱 微信</button>
            <button class="pay-btn blue2" @click="openPay('支付宝')">📱 支付宝</button>
            <button class="pay-btn orange" @click="openPay('储值')">💳 储值</button>
          </div>
          <button class="settle-btn" :disabled="cart.length === 0" @click="settle">
            结 算（F9）
          </button>
        </div>
      </aside>
    </div>

    <!-- 挂单抽屉：左侧滑出 -->
    <el-drawer v-model="hangDrawer" title="挂单管理" size="380px">
      <div v-if="hangOrders.length === 0" class="hang-empty">暂无挂单</div>
      <div v-for="(h, i) in hangOrders" :key="i" class="hang-item">
        <div class="hang-info">
          <div class="hang-time num">{{ h.time }}</div>
          <div class="hang-items">{{ h.items }} 项</div>
          <div class="hang-amount num">¥{{ h.amount.toFixed(2) }}</div>
        </div>
        <div class="hang-ops">
          <el-button type="primary" @click="resumeHang(i)">取单</el-button>
          <el-button text type="danger" @click="removeHang(i)">删除</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 支付弹窗 -->
    <el-dialog v-model="payDialog" :title="`${payMethod} 收款`" width="420px" :show-close="false">
      <div class="pay-dialog">
        <div class="pay-amount num">¥{{ totalAmount.toFixed(2) }}</div>
        <div v-if="payMethod === '现金'" class="cash-input">
          <el-input v-model="cashReceived" size="large" placeholder="输入实收金额" class="num" />
          <div class="change-row">
            找零：<span class="num change-value">¥{{ changeAmount.toFixed(2) }}</span>
          </div>
        </div>
        <div v-else-if="payMethod === '储值'" class="cash-input">
          <el-input v-model="memberMobile" size="large" placeholder="输入会员手机号" />
        </div>
        <div v-else class="scan-tip">
          <div class="scan-icon">📷</div>
          <p>请用扫描枪扫描顾客{{ payMethod }}付款码</p>
          <el-tag type="info" effect="light">扫码记账 · 预留官方支付接口</el-tag>
        </div>
        <el-button type="primary" size="large" class="confirm-pay" @click="confirmPay">
          确认收款
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Printer, RefreshLeft, Switch, Setting } from '@element-plus/icons-vue'

const router = useRouter()

/* ---------- 模拟数据：商品与分类 ---------- */
const categories = ['全部', '蔬菜', '水果', '肉类', '水产', '粮油副食']

// 商品列表（pricingMode: weigh=称重商品，count=按件标准品）
const products = [
  { id: 1, name: '上海青', price: 4.8, unit: 'kg', pricingMode: 'weigh', cate: '蔬菜', pinyin: 'shq' },
  { id: 2, name: '西红柿', price: 6.5, unit: 'kg', pricingMode: 'weigh', cate: '蔬菜', pinyin: 'xhs' },
  { id: 3, name: '黄瓜', price: 5.2, unit: 'kg', pricingMode: 'weigh', cate: '蔬菜', pinyin: 'hg' },
  { id: 4, name: '土豆', price: 3.8, unit: 'kg', pricingMode: 'weigh', cate: '蔬菜', pinyin: 'td' },
  { id: 5, name: '蜜桔', price: 7.9, unit: 'kg', pricingMode: 'weigh', cate: '水果', pinyin: 'mj' },
  { id: 6, name: '红富士苹果', price: 9.8, unit: 'kg', pricingMode: 'weigh', cate: '水果', pinyin: 'hfs' },
  { id: 7, name: '香蕉', price: 5.6, unit: 'kg', pricingMode: 'weigh', cate: '水果', pinyin: 'xj' },
  { id: 8, name: '五花肉', price: 28.8, unit: 'kg', pricingMode: 'weigh', cate: '肉类', pinyin: 'whr' },
  { id: 9, name: '前腿肉', price: 25.6, unit: 'kg', pricingMode: 'weigh', cate: '肉类', pinyin: 'qtr' },
  { id: 10, name: '鸡胸肉', price: 21.5, unit: 'kg', pricingMode: 'weigh', cate: '肉类', pinyin: 'jxr' },
  { id: 11, name: '草鱼', price: 15.8, unit: 'kg', pricingMode: 'weigh', cate: '水产', pinyin: 'cy' },
  { id: 12, name: '基围虾', price: 42.0, unit: 'kg', pricingMode: 'weigh', cate: '水产', pinyin: 'jwx' },
  { id: 13, name: '东北大米', price: 5.5, unit: 'kg', pricingMode: 'weigh', cate: '粮油副食', pinyin: 'dbdm' },
  { id: 14, name: '鲜鸡蛋(盒)', price: 13.8, unit: '盒', pricingMode: 'count', cate: '粮油副食', pinyin: 'xjd' },
  { id: 15, name: '金龙鱼花生油', price: 89.9, unit: '瓶', pricingMode: 'count', cate: '粮油副食', pinyin: 'jly' },
  { id: 16, name: '挂面(袋)', price: 6.9, unit: '袋', pricingMode: 'count', cate: '粮油副食', pinyin: 'gm' },
]

const keyword = ref('')
const currentCate = ref('全部')

// 商品筛选：按分类 + 关键字（名称/拼音码）
const filteredProducts = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return products.filter((p) => {
    const inCate = currentCate.value === '全部' || p.cate === currentCate.value
    const inKw = !kw || p.name.includes(kw) || p.pinyin.includes(kw)
    return inCate && inKw
  })
})

/* ---------- 购物车 ---------- */
const cart = ref([])

// 购物车合计金额
const totalAmount = computed(() => cart.value.reduce((s, i) => s + i.amount, 0))
const discount = ref(0) // 整单优惠（模拟：满100减5）

// 添加商品：称重商品进入称重流程，按件商品直接入单
const addProduct = (p) => {
  if (p.pricingMode === 'count') {
    const existing = cart.value.find((i) => i.productId === p.id)
    if (existing) {
      existing.qty += 1
      existing.amount = existing.qty * existing.price
    } else {
      cart.value.push({
        productId: p.id, name: p.name, price: p.price, qty: 1,
        weighted: false, amount: p.price, weightKey: 'count',
      })
    }
    ElMessage.success(`已加入：${p.name}`)
    return
  }
  // 称重商品：选中后开始称重流程
  currentProduct.value = p
  manualWeight.value = false
  startWeighing()
}

const incItem = (item) => {
  item.qty += 1
  item.amount = item.qty * item.price
}
const decItem = (item) => {
  if (item.qty <= 1) return removeItem(item)
  item.qty -= 1
  item.amount = item.qty * item.price
}
const removeItem = (item) => {
  cart.value = cart.value.filter((i) => i !== item)
}
const clearCart = () => {
  cart.value = []
  discount.value = 0
}

/* ---------- 称重模拟（模拟秤） ---------- */
const currentProduct = ref(null)
const weight = ref(0)
const weightStable = ref(false)
const manualWeight = ref(false)

// 重量显示：去皮后净重
const weightDisplay = computed(() => {
  if (manualWeight.value) return '0.00'
  return (weight.value - tareOffset.value).toFixed(2)
})
const weightUnit = computed(() => (currentProduct.value ? 'kg' : ''))
const scaleStable = computed(() => weightStable.value)
const scaleOnline = ref(true)
const tareOffset = ref(0)

let weighTimer = null
let stableCount = 0

// 开始模拟称重：重量渐增至固定目标后小幅抖动，连续稳定判定
const startWeighing = () => {
  stopWeighing()
  weight.value = 0
  weightStable.value = false
  stableCount = 0
  tareOffset.value = 0
  // 固定目标重量：仅在称重开始时随机一次，之后重量向该目标收敛
  const target = 0.5 + Math.random() * 0.8
  weighTimer = setInterval(() => {
    if (weight.value < target) {
      // 未达到目标：按步长渐增（模拟放上秤盘的过程）
      weight.value = Math.min(target, weight.value + 0.2 + Math.random() * 0.25)
    } else {
      // 已达到目标：±0.005 小幅抖动（模拟真实秤的微小波动）
      weight.value = target + (Math.random() - 0.5) * 0.01
    }
    const cur = weight.value - tareOffset.value
    const delta = Math.abs(cur - prevWeight)
    prevWeight = cur
    if (delta < 0.02 && cur > 0.05) {
      stableCount += 1
    } else {
      stableCount = 0
    }
    // 连续 3 次稳定 → 自动确认计价
    if (stableCount >= 3) {
      weightStable.value = true
      if (weight.value > 0.01) {
        confirmWeight()
      }
    }
  }, 260)
}
let prevWeight = 0

// 停止模拟称重
const stopWeighing = () => {
  if (weighTimer) clearInterval(weighTimer)
  weighTimer = null
}

// 稳定后自动确认：重量 × 单价 入购物车（默认自动，可配置为手动）
const confirmWeight = () => {
  const net = weight.value - tareOffset.value
  if (net <= 0.001 || !currentProduct.value) return
  const p = currentProduct.value
  const amount = net * p.price
  cart.value.push({
    productId: p.id, name: p.name, price: p.price, qty: 1,
    weighted: true, weight: +net.toFixed(2),
    amount: +amount.toFixed(2), weightKey: Date.now(),
  })
  ElMessage.success(`${p.name} ${net.toFixed(2)}kg · ¥${amount.toFixed(2)}`)
  stopWeighing()
  currentProduct.value = null
}

// 去皮：当前重量作为皮重
const doTare = () => {
  tareOffset.value = weight.value
  weightStable.value = false
  ElMessage.success('已去皮')
}

// 置零
const doZero = () => {
  tareOffset.value = 0
  weight.value = 0
  ElMessage.success('已置零')
}

/* ---------- 支付 ---------- */
const payDialog = ref(false)
const payMethod = ref('现金')
const cashReceived = ref('')
const memberMobile = ref('')

// 找零计算
const changeAmount = computed(() => {
  const rec = parseFloat(cashReceived.value)
  return isNaN(rec) ? 0 : Math.max(0, rec - totalAmount.value)
})

// 打开支付弹窗
const openPay = (method) => {
  if (cart.value.length === 0) {
    ElMessage.warning('购物车为空')
    return
  }
  payMethod.value = method
  payDialog.value = true
}

// 确认收款：模拟结算成功，打印小票 + 称重商品打标签
const confirmPay = () => {
  if (payMethod.value === '现金') {
    const rec = parseFloat(cashReceived.value)
    if (isNaN(rec) || rec < totalAmount.value) {
      ElMessage.warning('实收金额不足')
      return
    }
  }
  if (payMethod.value === '储值' && !memberMobile.value) {
    ElMessage.warning('请输入会员手机号')
    return
  }
  const weightedCount = cart.value.filter((i) => i.weighted).length
  payDialog.value = false
  // 重置支付输入，避免下次打开残留上次的实收金额/手机号
  cashReceived.value = ''
  memberMobile.value = ''
  ElMessage.success(
    `收款成功 ¥${totalAmount.value.toFixed(2)} · 已打印小票${weightedCount ? ` + ${weightedCount}张价格标签` : ''}`,
  )
  clearCart()
}

// 结算快捷键 F9
const settle = () => {
  openPay('现金')
}

/* ---------- 挂单 ---------- */
const hangDrawer = ref(false)
const hangOrders = ref([])

// 挂单：保存当前购物车并清空
const hangOrder = () => {
  if (cart.value.length === 0) return
  hangOrders.value.unshift({
    items: cart.value.map((i) => i.name).join('、'),
    count: cart.value.length,
    amount: totalAmount.value,
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    snapshot: JSON.parse(JSON.stringify(cart.value)),
  })
  clearCart()
  ElMessage.success('已挂单')
}

// 取单：恢复购物车
const resumeHang = (i) => {
  cart.value = hangOrders.value[i].snapshot
  hangOrders.value.splice(i, 1)
  hangDrawer.value = false
  ElMessage.success('已取单')
}

const removeHang = (i) => {
  hangOrders.value.splice(i, 1)
}

/* ---------- 时钟与快捷键 ---------- */
const now = ref('')

// 更新时间显示
const updateClock = () => {
  now.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

// 全局快捷键：F9 结算、F10 挂单、Esc 清空
const onKeydown = (e) => {
  if (e.key === 'F9') {
    e.preventDefault()
    settle()
  } else if (e.key === 'F10') {
    e.preventDefault()
    hangOrder()
  } else if (e.key === 'Escape') {
    clearCart()
  }
}

onMounted(() => {
  updateClock()
  setInterval(updateClock, 1000)
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  stopWeighing()
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.pos-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ----- 顶部栏 ----- */
.pos-header {
  height: 64px;
  background: var(--neutral-900);
  color: #fff;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 20px;
  flex-shrink: 0;
}
.store-name {
  font-size: 19px;
  font-weight: 600;
}
.header-meta {
  display: flex;
  gap: 10px;
  margin-top: 2px;
}
.shift-chip,
.sync-chip {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  background: oklch(30% 0.02 152);
  color: oklch(85% 0.02 152);
}
.sync-chip.ok {
  background: oklch(40% 0.09 152 / 0.5);
  color: oklch(88% 0.08 152);
}
.header-clock {
  margin-left: auto;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 1px;
}
.header-actions {
  display: flex;
  gap: 10px;
}
.header-actions :deep(.el-button) {
  border-radius: 10px;
}

/* ----- 主体三栏 ----- */
.pos-body {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1.15fr 0.95fr;
  gap: 12px;
  padding: 12px;
  min-height: 0;
}

/* ----- 左栏：商品 ----- */
.col-products {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.search-bar :deep(.el-input__inner) {
  font-size: 17px;
}
.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cat-tab {
  border: none;
  cursor: pointer;
  padding: 8px 18px;
  border-radius: 999px;
  font-size: 15px;
  background: #fff;
  color: var(--neutral-600);
  border: 1px solid var(--neutral-200);
  transition: all 0.15s;
}
.cat-tab.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
  font-weight: 600;
}
.product-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  overflow: auto;
  padding-bottom: 8px;
}
.product-cell {
  position: relative;
  border: none;
  cursor: pointer;
  border-radius: 12px;
  background: #fff;
  padding: 14px 12px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--neutral-200);
  text-align: left;
  transition: transform 0.1s;
}
.product-cell:hover {
  transform: translateY(-2px);
  border-color: var(--brand);
}
.product-cell.weighted {
  border-left: 4px solid var(--accent);
}
.p-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-800);
  margin-bottom: 6px;
}
.p-price {
  font-size: 20px;
  font-weight: 700;
  color: var(--danger);
}
.p-unit {
  font-size: 12px;
  color: var(--neutral-400);
  margin-top: 2px;
}
.p-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 11px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 600;
}

/* ----- 中栏：购物车 ----- */
.col-cart {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--neutral-200);
  min-height: 0;
}
.cart-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--neutral-200);
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-800);
}
.cart-list {
  flex: 1;
  overflow: auto;
  padding: 8px 12px;
}
.cart-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--neutral-400);
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 8px;
}
.cart-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid var(--neutral-100);
}
.ci-name {
  font-size: 15px;
  font-weight: 500;
}
.ci-sub {
  font-size: 13px;
  color: var(--neutral-400);
  margin-top: 2px;
}
.ci-amount {
  font-size: 18px;
  font-weight: 700;
  color: var(--neutral-900);
  text-align: right;
}
.ci-ops {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  justify-content: flex-end;
}
.op-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--neutral-200);
  background: #fff;
  font-size: 17px;
  cursor: pointer;
  color: var(--neutral-700);
}
.op-btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.op-btn.danger:hover {
  border-color: var(--danger);
  color: var(--danger);
}

/* ----- 右栏：称重 + 结算 ----- */
.col-settle {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.weight-card {
  background: var(--neutral-900);
  border-radius: var(--radius-lg);
  padding: 18px;
  color: #fff;
  text-align: center;
}
.weight-card.stable {
  background: linear-gradient(160deg, var(--neutral-900), oklch(30% 0.1 152));
}
.weight-label {
  font-size: 14px;
  color: oklch(82% 0.03 152);
  min-height: 22px;
}
.weight-value {
  font-size: 68px;
  font-weight: 700;
  line-height: 1.2;
  color: #fff;
  margin-top: 4px;
}
.weight-unit {
  font-size: 16px;
  color: oklch(80% 0.03 152);
}
.weight-state {
  margin-top: 10px;
  font-size: 14px;
  color: oklch(75% 0.05 60);
}
.weight-state.ok {
  color: oklch(80% 0.15 155);
  font-weight: 600;
}
.scale-ops {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}
.scale-btn {
  flex: 1;
  padding: 12px 0;
  border-radius: 10px;
  border: 1px solid oklch(60% 0.03 152);
  background: oklch(30% 0.02 152);
  color: #fff;
  font-size: 16px;
  cursor: pointer;
}
.scale-btn:hover {
  background: oklch(40% 0.05 152);
}
.scale-status {
  margin-top: 12px;
  font-size: 12px;
  color: oklch(75% 0.03 152);
}
.scale-status.online {
  color: oklch(80% 0.1 155);
}
.manual-link {
  margin-left: 8px;
  color: var(--accent);
  cursor: pointer;
  text-decoration: underline;
}
.total-card {
  flex: 1;
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--neutral-200);
  display: flex;
  flex-direction: column;
}
.total-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
}
.total-row span:first-child {
  font-size: 15px;
  color: var(--neutral-500);
}
.total-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--neutral-900);
}
.discount-row {
  font-size: 13px;
  color: var(--success);
  text-align: right;
  margin-bottom: 12px;
}
.pay-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.pay-btn {
  padding: 16px 0;
  border: none;
  border-radius: 12px;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  color: #fff;
  background: var(--warning);
}
.pay-btn.blue { background: oklch(56% 0.16 235); }
.pay-btn.blue2 { background: oklch(62% 0.15 170); }
.pay-btn.orange { background: var(--accent-deep); }
.pay-btn:hover {
  filter: brightness(1.08);
}
.settle-btn {
  margin-top: 12px;
  padding: 20px 0;
  border: none;
  border-radius: 12px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 4px;
  cursor: pointer;
  color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-deep));
  box-shadow: 0 4px 12px oklch(52% 0.15 152 / 0.4);
}
.settle-btn:disabled {
  background: var(--neutral-300);
  box-shadow: none;
  cursor: not-allowed;
}

/* ----- 支付弹窗 ----- */
.pay-dialog {
  text-align: center;
}
.pay-amount {
  font-size: 40px;
  font-weight: 700;
  color: var(--neutral-900);
  margin-bottom: 18px;
}
.cash-input {
  margin-bottom: 14px;
}
.change-row {
  margin-top: 10px;
  font-size: 16px;
  color: var(--neutral-600);
}
.change-value {
  color: var(--success);
  font-weight: 700;
  font-size: 20px;
}
.scan-tip {
  padding: 12px 0;
  color: var(--neutral-500);
}
.scan-icon {
  font-size: 52px;
  margin-bottom: 8px;
}
.confirm-pay {
  width: 100%;
  margin-top: 8px;
  height: 48px;
  font-size: 18px;
}

/* ----- 挂单抽屉 ----- */
.hang-empty {
  color: var(--neutral-400);
  text-align: center;
  padding: 40px 0;
}
.hang-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px;
  border: 1px solid var(--neutral-200);
  border-radius: 10px;
  margin-bottom: 10px;
}
.hang-time {
  font-size: 13px;
  color: var(--neutral-400);
}
.hang-items {
  font-size: 15px;
  font-weight: 500;
  margin: 4px 0;
}
.hang-amount {
  font-size: 18px;
  font-weight: 700;
}
</style>
