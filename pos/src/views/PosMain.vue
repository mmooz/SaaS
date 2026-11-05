<template>
  <div class="pos-page">
    <!-- ===== 顶部栏 ===== -->
    <header class="pos-header">
      <div class="header-left">
        <div class="store-name">鲜果超市 · 1号收银台</div>
        <div class="header-meta">
          <span class="shift-chip">早班 · 08:00 接班</span>
          <span class="shift-chip">{{ cashierName }}</span>
          <span class="sync-chip" :class="syncClass">{{ syncText }}</span>
        </div>
      </div>
      <div class="header-clock num">{{ now }}</div>
      <div class="header-actions">
        <el-button size="large" @click="hangDrawer = true"><el-icon><Folder /></el-icon>&nbsp;挂单</el-button>
        <el-button size="large" @click="$router.push('/reprint')"><el-icon><Printer /></el-icon>&nbsp;补打</el-button>
        <el-button size="large" @click="$router.push('/refund')"><el-icon><RefreshLeft /></el-icon>&nbsp;退款</el-button>
        <el-button size="large" @click="$router.push('/shift')"><el-icon><Switch /></el-icon>&nbsp;交接班</el-button>
        <el-button size="large" @click="$router.push('/settings')"><el-icon><Setting /></el-icon></el-button>
        <el-button size="large" @click="logout"><el-icon><SwitchButton /></el-icon>&nbsp;退出</el-button>
      </div>
    </header>

    <!-- ===== 主体三栏 ===== -->
    <div class="pos-body">
      <!-- 左栏：分类 + 商品 -->
      <aside class="col-products">
        <div class="search-bar">
          <el-input v-model="keyword" placeholder="扫码 / 商品名 / 拼音码" size="large" clearable @keyup.enter="handleScan">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="category-tabs">
          <button
            v-for="c in categoryTabs"
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
          <div v-if="filteredProducts.length === 0" class="empty-products">
            暂无商品，请在后台录入并同步
          </div>
        </div>
      </aside>

      <!-- 中栏：购物车 -->
      <section class="col-cart">
        <div class="cart-head">
          <span>购物车（{{ store.cartCount }} 项）</span>
          <el-button text @click="store.clearCart">清空</el-button>
        </div>
        <div class="cart-list">
          <div v-if="store.cart.length === 0" class="cart-empty">
            <div class="empty-icon">🛒</div>
            <p>请选择商品或放上秤盘</p>
          </div>
          <div v-for="item in store.cart" :key="item.productId + item.weightKey" class="cart-item">
            <div class="ci-main">
              <div class="ci-name">{{ item.name }}</div>
              <div class="ci-sub num">
                <template v-if="item.weighted">
                  {{ item.weight.toFixed(2) }} kg × ¥{{ store.itemPrice(item).toFixed(2) }}
                </template>
                <template v-else>× {{ item.qty }} · ¥{{ store.itemPrice(item).toFixed(2) }}</template>
              </div>
            </div>
            <div class="ci-right">
              <div class="ci-amount num">¥{{ store.itemAmount(item).toFixed(2) }}</div>
              <div class="ci-ops">
                <button class="op-btn" @click="store.decItem(item)">−</button>
                <button class="op-btn" @click="store.incItem(item)">+</button>
                <button class="op-btn danger" @click="store.removeItem(item)">✕</button>
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
          <!-- 会员识别卡：散客 / 已识别会员 -->
          <div class="member-card" :class="{ active: store.memberActive }">
            <template v-if="store.member">
              <div class="member-main">
                <div class="member-name">
                  {{ store.member.name || '会员' }}
                  <span class="member-level">{{ levelText(store.member.level) }}</span>
                </div>
                <div class="member-sub num">
                  {{ store.member.mobile }} · 积分 {{ store.member.points }} · 余额 ¥{{ store.member.balance.toFixed(2) }}
                </div>
              </div>
              <el-button text type="danger" size="small" @click="store.clearMember">取消会员</el-button>
            </template>
            <template v-else>
              <div class="member-sub">散客 · 识别会员享会员价</div>
              <el-button size="small" type="primary" @click="openMemberDialog">会员识别</el-button>
            </template>
          </div>
          <div class="total-row">
            <span>应收合计</span>
            <span class="total-value num">¥{{ store.totalAmount.toFixed(2) }}</span>
          </div>
          <div class="discount-row num" v-if="store.itemDiscount > 0">
            优惠（会员价/特价） −¥{{ store.itemDiscount.toFixed(2) }}
          </div>
          <div class="discount-row num" v-if="store.orderDiscount > 0">
            满减优惠 −¥{{ store.orderDiscount.toFixed(2) }}
          </div>
          <div v-if="store.hasOfflineOrders" class="offline-tip">
            有 {{ store.offlineOrders.length }} 笔订单待上传
            <el-button link size="small" type="primary" @click="flushOffline">立即重传</el-button>
          </div>
          <div class="pay-buttons">
            <button class="pay-btn" @click="openPay('现金')">💵 现金</button>
            <button class="pay-btn blue" @click="openPay('微信')">📱 微信</button>
            <button class="pay-btn blue2" @click="openPay('支付宝')">📱 支付宝</button>
            <button class="pay-btn orange" @click="openPay('储值')">💳 储值</button>
          </div>
          <div class="print-row">
            <el-checkbox v-model="autoPrint" size="large" @change="saveAutoPrint">
              结算后自动打印小票 / 标签
            </el-checkbox>
          </div>
          <button class="settle-btn" :disabled="store.cart.length === 0" @click="settle">
            结 算（F9）
          </button>
        </div>
      </aside>
    </div>

    <!-- 挂单抽屉 -->
    <el-drawer v-model="hangDrawer" title="挂单管理" size="380px">
      <div v-if="store.hangOrders.length === 0" class="hang-empty">暂无挂单</div>
      <div v-for="(h, i) in store.hangOrders" :key="i" class="hang-item">
        <div class="hang-info">
          <div class="hang-time num">{{ h.time }}</div>
          <div class="hang-items">{{ h.count }} 项</div>
          <div class="hang-amount num">¥{{ h.amount.toFixed(2) }}</div>
        </div>
        <div class="hang-ops">
          <el-button type="primary" @click="store.resumeHang(i)">取单</el-button>
          <el-button text type="danger" @click="store.removeHang(i)">删除</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 支付弹窗 -->
    <el-dialog v-model="payDialog" :title="`${payMethod} 收款`" width="420px" :show-close="false">
      <div class="pay-dialog">
        <div class="pay-amount num">¥{{ store.totalAmount.toFixed(2) }}</div>
        <div v-if="payMethod === '现金'" class="cash-input">
          <el-input v-model="cashReceived" size="large" placeholder="输入实收金额" class="num" />
          <div class="change-row">
            找零：<span class="num change-value">¥{{ changeAmount.toFixed(2) }}</span>
          </div>
        </div>
        <div v-else-if="payMethod === '储值'" class="cash-input">
          <div v-if="store.member" class="member-pay-info num">
            会员余额 ¥{{ store.member.balance.toFixed(2) }} · 本单应收 ¥{{ store.totalAmount.toFixed(2) }}
          </div>
          <div v-else class="pay-tip">请先识别会员后再使用储值支付</div>
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

    <!-- 会员识别弹窗 -->
    <el-dialog v-model="memberDialog" title="会员识别" width="420px">
      <div class="member-dialog">
        <el-input
          v-model="memberInputMobile"
          size="large"
          placeholder="输入手机号 / 扫描会员码"
          clearable
          @keyup.enter="identifyMember"
        />
        <div class="member-actions">
          <el-button size="large" @click="identifyMember">查 询</el-button>
          <el-button size="large" type="primary" :loading="memberLoading" @click="registerMember">
            快速建档
          </el-button>
        </div>
        <div class="member-tip">新顾客可直接建档，建档后立即识别并享会员价</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Search, Printer, RefreshLeft, Switch, Setting, Folder, SwitchButton,
} from '@element-plus/icons-vue'
import { usePosStore } from '../stores/posStore'
import { PrintService } from '../services/print/PrintService'
import { OrderPrintMapper } from '../services/print/OrderPrintMapper'
import { LabelCode } from '../services/print/LabelCode'
import { createMember, fetchMemberByMobile } from '../api'
import { TauriScaleService } from '../services/scale/TauriScaleService'

const router = useRouter()
const store = usePosStore()

// 当前登录收银员名称（未登录时显示提示）
const cashierName = computed(() => (store.cashier ? store.cashier.name : '未登录'))

// 退出登录：清空收银员会话并返回登录页
const logout = () => {
  store.clearCashier()
  ElMessage.success('已退出登录')
  router.push('/login')
}

/* ---------- 演示兜底数据（后端无数据时使用） ---------- */
const fallbackProducts = [
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

/* ---------- 商品来源：优先后端同步数据，空则用演示数据 ---------- */
const products = computed(() => {
  if (store.products.length) {
    // 后端商品字段转换：pricing_mode -> pricingMode，member_price -> memberPrice
    return store.products.map((p) => ({
      id: p.id,
      name: p.name,
      price: p.price,
      unit: p.unit,
      pricingMode: p.pricing_mode,
      memberPrice: p.member_price ?? null,
      categoryId: p.category_id ?? null,
      pinyin: p.pinyin || '',
      cate: store.categoryName(p.category_id) || '',
      barcode: p.barcode,
    }))
  }
  // 演示数据统一按零售价 95 折生成会员价
  return fallbackProducts.map((p) => ({ ...p, memberPrice: +(p.price * 0.95).toFixed(2) }))
})

// 分类页签：'全部' + 后端一级分类名（无数据时用演示数据分类）
const categoryTabs = computed(() => {
  const names = new Set(['全部'])
  products.value.forEach((p) => p.cate && names.add(p.cate))
  return [...names]
})

const keyword = ref('')
const currentCate = ref('全部')

// 商品筛选：按分类 + 关键字
const filteredProducts = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return products.value.filter((p) => {
    const inCate = currentCate.value === '全部' || p.cate === currentCate.value
    const inKw = !kw || p.name.includes(kw) || p.pinyin.includes(kw) || p.barcode?.includes(kw)
    return inCate && inKw
  })
})

/* ---------- 添加商品 ---------- */
const currentProduct = ref(null)

// 添加商品：按件直接入单，称重进入称重流程
const addProduct = (p) => {
  if (p.pricingMode === 'count') {
    store.addCountProduct(p)
    ElMessage.success(`已加入：${p.name}`)
    return
  }
  currentProduct.value = p
  manualWeight.value = false
  startWeighing()
}

// 扫码回车：优先匹配商品条码，其次解析称重标签码
const handleScan = () => {
  const code = keyword.value.trim()
  if (!code) return

  // 1) 商品自有条码精确匹配
  const byBarcode = products.value.find((p) => p.barcode && String(p.barcode) === code)
  if (byBarcode) {
    keyword.value = ''
    if (byBarcode.pricingMode === 'count') {
      store.addCountProduct(byBarcode)
      ElMessage.success(`已加入：${byBarcode.name}`)
    } else {
      currentProduct.value = byBarcode
      manualWeight.value = false
      startWeighing()
      ElMessage.info(`请将「${byBarcode.name}」放上秤盘称重`)
    }
    return
  }

  // 2) 称重标签码：解析商品与重量后直接入车
  const label = LabelCode.parse(code)
  if (label) {
    const product = products.value.find(
      (p) => p.id === label.productId && p.pricingMode === 'weigh',
    )
    if (!product) {
      ElMessage.warning(`标签商品不存在：#${label.productId}`)
      return
    }
    if (label.weight <= 0) {
      ElMessage.warning('标签重量无效')
      return
    }
    store.confirmWeighted(product, label.weight)
    keyword.value = ''
    ElMessage.success(`${product.name} ${label.weight.toFixed(2)}kg · ¥${(label.weight * product.price).toFixed(2)}`)
    return
  }

  ElMessage.warning('未找到对应商品或标签码')
}

/* ---------- 电子秤接入（原生串口/网口，浏览器降级模拟秤） ---------- */
const weight = ref(0)
const weightStable = ref(false)
const manualWeight = ref(false)
const tareOffset = ref(0)
const scaleOnline = ref(false)
// 是否已连接原生秤（false 时使用本地模拟称重）
const nativeScale = ref(false)

/**
 * 读取本地保存的秤设置
 * @returns {object} 秤设置（connectMode/comPort/baudRate/stableCount/autoConfirm 等）
 */
const loadScaleSettings = () => {
  try {
    const raw = localStorage.getItem('pos_settings')
    const data = raw ? JSON.parse(raw) : null
    return data?.scale || {}
  } catch {
    return {}
  }
}

// 当前生效的秤设置（连接与稳定判定使用）
const scaleSettings = loadScaleSettings()

const weightDisplay = computed(() => {
  if (manualWeight.value) return '0.00'
  return weight.value.toFixed(2)
})
const weightUnit = computed(() => (currentProduct.value ? 'kg' : ''))
const scaleStable = computed(() => weightStable.value)

let weighTimer = null
let stableCount = 0
let prevWeight = 0
// 原生秤读取中标记，避免异步读取重叠
let reading = false
// 模拟秤毛重（去皮偏移在其上扣减）
let simGross = 0

/**
 * 稳定判定：连续 N 次读数变化小于阈值即视为稳定，并按设置自动入单
 * @param {number} cur 当前净重 kg
 */
const updateStability = (cur) => {
  const delta = Math.abs(cur - prevWeight)
  prevWeight = cur
  if (delta < 0.02 && cur > 0.05) {
    stableCount += 1
  } else {
    stableCount = 0
  }
  const need = Math.max(1, Number(scaleSettings.stableCount) || 3)
  if (stableCount >= need) {
    weightStable.value = true
    if (scaleSettings.autoConfirm !== false && cur > 0.01) confirmWeight()
  }
}

/**
 * 读取原生秤重量（串口/网口/内置模拟秤）
 * @returns {Promise<void>}
 */
const readNativeWeight = async () => {
  if (reading) return
  reading = true
  try {
    const value = await TauriScaleService.readWeight()
    weight.value = Math.max(0, Number(value) || 0)
    updateStability(weight.value)
  } catch {
    // 未读到有效帧时保持上次重量，等待下一帧
  } finally {
    reading = false
  }
}

// 开始称重：已连接原生秤时读取真实重量，否则使用本地模拟
const startWeighing = () => {
  stopWeighing()
  weight.value = 0
  weightStable.value = false
  manualWeight.value = false
  stableCount = 0
  prevWeight = 0
  tareOffset.value = 0
  simGross = 0
  if (nativeScale.value) {
    weighTimer = setInterval(readNativeWeight, 250)
    return
  }
  // 模拟秤：毛重渐增至固定目标后小幅抖动
  const target = 0.5 + Math.random() * 0.8
  weighTimer = setInterval(() => {
    if (simGross < target) {
      simGross = Math.min(target, simGross + 0.2 + Math.random() * 0.25)
    } else {
      simGross = target + (Math.random() - 0.5) * 0.01
    }
    weight.value = Math.max(0, simGross - tareOffset.value)
    updateStability(weight.value)
  }, 260)
}

// 停止称重轮询
const stopWeighing = () => {
  if (weighTimer) clearInterval(weighTimer)
  weighTimer = null
}

// 稳定后确认：入购物车
const confirmWeight = () => {
  const net = weight.value
  if (net <= 0.001 || !currentProduct.value) return
  const p = currentProduct.value
  store.confirmWeighted(p, net)
  ElMessage.success(`${p.name} ${net.toFixed(2)}kg · ¥${(net * p.price).toFixed(2)}`)
  stopWeighing()
  currentProduct.value = null
}

// 去皮
const doTare = async () => {
  weightStable.value = false
  if (nativeScale.value) {
    try {
      await TauriScaleService.tare()
      weight.value = 0
    } catch (err) {
      ElMessage.error(`去皮失败：${err.message}`)
      return
    }
  } else {
    // 模拟秤：以当前毛重作为皮重
    tareOffset.value = simGross
    weight.value = 0
  }
  ElMessage.success('已去皮')
}

// 置零
const doZero = async () => {
  if (nativeScale.value) {
    try {
      await TauriScaleService.zero()
    } catch (err) {
      ElMessage.error(`置零失败：${err.message}`)
      return
    }
  }
  tareOffset.value = 0
  simGross = 0
  weight.value = 0
  weightStable.value = false
  ElMessage.success('已置零')
}

/* ---------- 会员识别 ---------- */
const memberDialog = ref(false) // 会员识别弹窗
const memberInputMobile = ref('') // 待识别的手机号
const memberLoading = ref(false) // 建档/查询请求中

// 打开会员识别弹窗（清空上次输入）
const openMemberDialog = () => {
  memberInputMobile.value = ''
  memberDialog.value = true
}

// 等级文案
const levelText = (level) => ({ normal: '普通会员', silver: '银卡', gold: '金卡' }[level] || '普通会员')

// 按手机号识别会员
const identifyMember = async () => {
  const mobile = memberInputMobile.value.trim()
  if (!mobile) {
    ElMessage.warning('请输入会员手机号')
    return
  }
  memberLoading.value = true
  try {
    const member = await fetchMemberByMobile(mobile)
    store.setMember(member)
    memberDialog.value = false
    ElMessage.success(`已识别会员：${member.name || member.mobile}`)
  } catch (err) {
    ElMessage.warning(err.message === '会员不存在' ? '未找到会员，可点击“快速建档”' : err.message)
  } finally {
    memberLoading.value = false
  }
}

// 快速建档并直接识别
const registerMember = async () => {
  const mobile = memberInputMobile.value.trim()
  if (!mobile) {
    ElMessage.warning('请输入手机号')
    return
  }
  memberLoading.value = true
  try {
    const member = await createMember({ mobile })
    store.setMember(member)
    memberDialog.value = false
    ElMessage.success('建档成功，已识别会员')
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    memberLoading.value = false
  }
}

/* ---------- 支付 ---------- */
const payDialog = ref(false)
const payMethod = ref('现金')
const cashReceived = ref('')

// 找零计算
const changeAmount = computed(() => {
  const rec = parseFloat(cashReceived.value)
  return isNaN(rec) ? 0 : Math.max(0, rec - store.totalAmount)
})

// 打开支付弹窗
const openPay = (method) => {
  if (store.cart.length === 0) {
    ElMessage.warning('购物车为空')
    return
  }
  // 储值支付必须先识别会员且有足够余额
  if (method === '储值') {
    if (!store.member) {
      ElMessage.warning('请先识别会员')
      openMemberDialog()
      return
    }
    if (store.member.balance < store.totalAmount) {
      ElMessage.warning('会员储值余额不足')
      return
    }
  }
  payMethod.value = method
  payDialog.value = true
}

// 结算后自动打印（本地持久化，默认开启）
const autoPrint = ref(localStorage.getItem('pos_auto_print') !== '0')

// 保存自动打印开关
const saveAutoPrint = (value) => {
  localStorage.setItem('pos_auto_print', value ? '1' : '0')
}

// 确认收款：上传订单到服务端，失败则离线保存；成功后按设置自动打印
const confirmPay = async () => {
  if (payMethod.value === '现金') {
    const rec = parseFloat(cashReceived.value)
    if (isNaN(rec) || rec < store.totalAmount) {
      ElMessage.warning('实收金额不足')
      return
    }
  }
  if (payMethod.value === '储值') {
    if (!store.member) {
      ElMessage.warning('请先识别会员')
      return
    }
    if (store.member.balance < store.totalAmount) {
      ElMessage.warning('会员储值余额不足')
      return
    }
  }
  // 结算前快照，用于结算后打印（settle 会清空购物车）
  const meta = {
    cashierName: store.cashier ? store.cashier.name : '',
    payMethod: payMethod.value,
    cashReceived: payMethod.value === '现金' ? parseFloat(cashReceived.value) : undefined,
    change: payMethod.value === '现金' ? changeAmount.value : undefined,
    memberMobile: store.member ? store.member.mobile : '',
  }
  const weightedCount = store.cart.filter((i) => i.weighted).length
  // 结算会清空购物车，先记录应收金额用于提示文案
  const total = store.totalAmount
  payDialog.value = false
  const result = await store.settle({ payMethod: payMethod.value })
  if (result.ok) {
    ElMessage.success(
      `收款成功 ¥${total.toFixed(2)} · 已上传订单${weightedCount ? ` + ${weightedCount}张价格标签` : ''}`,
    )
    // 储值扣款与积分累计结果提示
    if (payMethod.value === '储值') {
      if (result.memberDeducted && store.member) {
        ElMessage.success(`储值已扣款 · 当前余额 ¥${store.member.balance.toFixed(2)} · 积分 ${store.member.points}`)
      } else {
        ElMessage.warning('储值扣款失败，请到后台核对会员余额')
      }
    }
  } else {
    ElMessage.warning(`离线收款成功 ¥${total.toFixed(2)} · 订单已存本机，联网后自动上传`)
  }
  // 自动打印：先小票（现金含实收/找零），再打印称重标签
  if (autoPrint.value && result.order) {
    const printOrder = OrderPrintMapper.fromSettle(result, meta)
    // 等待小票结果，打印机不可用时明确提示收银员
    const receiptResult = await PrintService.printReceipt(printOrder)
    if (receiptResult.channel === 'failed') {
      ElMessage.error(`小票打印失败：${receiptResult.reason}`)
    }
    setTimeout(async () => {
      const labelResult = await PrintService.printLabels(printOrder)
      if (labelResult.channel === 'failed') {
        ElMessage.error(`标签打印失败：${labelResult.reason}`)
      }
    }, 1200)
  }
  cashReceived.value = ''
}

// 结算快捷键 F9
const settle = () => openPay('现金')

// 重传离线数据（班次、订单、退款）
const flushOffline = async () => {
  const result = await store.flushOfflineOrders()
  if (!store.hasOfflineOrders) {
    ElMessage.success(result.uploaded ? `离线数据已全部上传（${result.uploaded} 单）` : '离线数据已全部上传')
  } else {
    ElMessage.warning('网络仍不可用，离线数据将在恢复联网后重试')
  }
}

// 网络恢复时自动补传离线数据
const handleOnline = async () => {
  const result = await store.flushOfflineOrders()
  if (result.uploaded > 0) ElMessage.success(`网络已恢复，自动补传 ${result.uploaded} 单`)
}

/* ---------- 挂单抽屉 ---------- */
const hangDrawer = ref(false)

/* ---------- 同步状态与时钟 ---------- */
const syncClass = computed(() => {
  if (store.syncState === 'error') return 'err'
  if (store.syncState === 'syncing') return 'busy'
  return 'ok'
})
const syncText = computed(() => {
  if (store.syncState === 'error') return '同步失败'
  if (store.syncState === 'syncing') return '同步中…'
  return store.lastSyncTime ? '已同步' : '未同步'
})

const now = ref('')
const updateClock = () => {
  now.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

// 全局快捷键：F9 结算、Esc 清空
const onKeydown = (e) => {
  if (e.key === 'F9') {
    e.preventDefault()
    settle()
  } else if (e.key === 'Escape') {
    store.clearCart()
  }
}

/**
 * 连接电子秤：桌面壳内按设置连接串口/网口秤，浏览器环境降级为模拟秤
 * @returns {Promise<void>}
 */
const connectScale = async () => {
  if (!TauriScaleService.isAvailable()) {
    nativeScale.value = false
    scaleOnline.value = true
    return
  }
  // 页面设置中网络模式对应 tcp，模拟秤对应 mock
  const connection = scaleSettings.connectMode === 'serial'
    ? 'serial'
    : scaleSettings.connectMode === 'network'
      ? 'tcp'
      : 'mock'
  try {
    const tcpAddr = `${scaleSettings.scaleIp || '192.168.1.100'}:${scaleSettings.scalePort || 5000}`
    await TauriScaleService.connect({
      connection,
      portName: scaleSettings.comPort,
      baudRate: scaleSettings.baudRate,
      tcpAddr,
    })
    nativeScale.value = true
    scaleOnline.value = await TauriScaleService.isConnected()
  } catch (err) {
    nativeScale.value = false
    scaleOnline.value = false
    ElMessage.warning(`电子秤连接失败，已降级为模拟称重：${err.message}`)
  }
}

onMounted(() => {
  updateClock()
  setInterval(updateClock, 1000)
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('online', handleOnline)
  // 连接电子秤（失败时使用模拟称重，不阻塞收银）
  connectScale()
  // 启动时恢复离线队列并补传，再同步商品数据（失败不阻塞，使用本地缓存）
  store.initOffline().then(() => {
    if (navigator.onLine) store.flushOfflineOrders()
  })
  store.syncProducts()
})
onBeforeUnmount(() => {
  stopWeighing()
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('online', handleOnline)
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
.sync-chip.err {
  background: oklch(40% 0.09 25 / 0.6);
  color: oklch(88% 0.08 25);
}
.sync-chip.busy {
  background: oklch(40% 0.09 60 / 0.6);
  color: oklch(90% 0.08 60);
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
  grid-template-columns: 1fr 0.5fr 0.5fr;
  gap: 12px;
  padding: 12px;
  min-height: 0;
}

/* ----- 左栏 ----- */
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
.empty-products {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--neutral-400);
  padding: 40px 0;
}

/* ----- 中栏 ----- */
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

/* ----- 右栏 ----- */
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

/* ----- 会员识别卡 ----- */
.member-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 12px;
  border: 1px dashed var(--neutral-300);
  border-radius: var(--radius-md);
  background: var(--neutral-50);
}
.member-card.active {
  border: 1px solid var(--brand);
  background: var(--brand-soft);
}
.member-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-900);
}
.member-level {
  font-size: 12px;
  font-weight: 500;
  color: var(--brand-deep);
  background: #fff;
  border: 1px solid var(--brand);
  border-radius: 999px;
  padding: 1px 8px;
  margin-left: 4px;
}
.member-sub {
  font-size: 13px;
  color: var(--neutral-500);
  margin-top: 3px;
}
.member-main {
  min-width: 0;
}
.offline-tip {
  font-size: 13px;
  color: var(--warning);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
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

/* ----- 会员识别弹窗 ----- */
.member-dialog {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.member-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.member-tip {
  font-size: 13px;
  color: var(--neutral-400);
  text-align: center;
}
.member-pay-info {
  font-size: 16px;
  color: var(--neutral-700);
}
.pay-tip {
  font-size: 15px;
  color: var(--warning);
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
