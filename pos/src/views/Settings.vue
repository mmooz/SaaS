<template>
  <div class="page">
    <!-- 顶部深色栏 -->
    <header class="page-header">
      <div class="header-title">系统设置</div>
      <el-button class="back-btn" @click="$router.push('/')"><el-icon><ArrowLeft /></el-icon>&nbsp;返回收银台</el-button>
    </header>

    <div class="page-body settings-body">
      <!-- 左侧竖排菜单 -->
      <aside class="side-menu">
        <button
          v-for="m in menus"
          :key="m.key"
          class="menu-item"
          :class="{ active: activeMenu === m.key }"
          @click="activeMenu = m.key"
        >
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </button>
      </aside>

      <!-- 右侧内容区 -->
      <section class="content-card">
        <!-- ===== 称重设置 ===== -->
        <template v-if="activeMenu === 'scale'">
          <div class="panel-title">称重设置</div>
          <el-form label-width="130px" class="set-form">
            <el-form-item label="秤连接方式">
              <el-select v-model="scaleForm.connectMode" size="large" class="set-input">
                <el-option label="串口" value="serial" />
                <el-option label="网口" value="network" />
                <el-option label="模拟秤" value="sim" />
              </el-select>
            </el-form-item>
            <el-form-item label="COM 口">
              <el-select v-model="scaleForm.comPort" size="large" class="set-input">
                <el-option v-for="p in comPorts" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
            <el-form-item label="波特率">
              <el-select v-model="scaleForm.baudRate" size="large" class="set-input">
                <el-option v-for="b in baudRates" :key="b" :label="String(b)" :value="b" />
              </el-select>
            </el-form-item>
            <el-form-item label="稳定自动确认">
              <el-switch v-model="scaleForm.autoConfirm" size="large" />
              <span class="field-tip">重量稳定后自动计价入单</span>
            </el-form-item>
            <el-form-item label="稳定次数">
              <el-input-number v-model="scaleForm.stableCount" :min="1" :max="10" size="large" />
              <span class="field-tip">连续 N 次读数一致判定为稳定</span>
            </el-form-item>
          </el-form>
          <!-- 串口协议说明卡片 -->
          <div class="proto-card">
            <div class="proto-title">串口协议说明</div>
            <p>· 数据格式：ASCII，一次重量上报为一帧，帧尾回车换行（\r\n）</p>
            <p>· 去皮指令：T；置零指令：Z；称重模式上报稳定重量</p>
            <p>· 波特率默认 9600，部分型号支持 4800，请按秤体标签设置</p>
          </div>
        </template>

        <!-- ===== 打印机 ===== -->
        <template v-else-if="activeMenu === 'printer'">
          <div class="panel-title">打印机</div>
          <!-- 打印通道与系统打印机列表 -->
          <div class="printer-block">
            <div class="printer-title">打印方式（原生直连）</div>
            <el-form label-width="90px" class="set-form">
              <el-form-item label="打印通道">
                <el-select v-model="printMode" size="large" class="set-input">
                  <el-option label="自动（优先原生直连）" value="auto" />
                  <el-option label="仅浏览器打印（HTML）" value="html" />
                </el-select>
                <span class="field-tip">{{ nativeTip }}</span>
              </el-form-item>
              <el-form-item label="系统打印机">
                <el-button class="big-btn" :loading="loadingPrinters" @click="loadSystemPrinters">
                  <el-icon><Refresh /></el-icon>&nbsp;刷新打印机列表
                </el-button>
              </el-form-item>
            </el-form>
          </div>
          <!-- 标签打印机 -->
          <div class="printer-block">
            <div class="printer-title">标签打印机（价格标签）</div>
            <el-form label-width="90px" class="set-form">
              <el-form-item label="系统打印机">
                <el-select
                  v-model="labelPrinter.systemName"
                  size="large"
                  class="set-input"
                  clearable
                  filterable
                  placeholder="未选择（使用浏览器打印）"
                >
                  <el-option v-for="p in systemPrinters" :key="p" :label="p" :value="p" />
                </el-select>
              </el-form-item>
              <el-form-item label="型号">
                <el-input v-model="labelPrinter.model" size="large" class="set-input" />
              </el-form-item>
              <el-form-item label="端口">
                <el-select v-model="labelPrinter.port" size="large" class="set-input">
                  <el-option label="USB" value="USB" />
                  <el-option label="并口" value="LPT1" />
                  <el-option label="网口" value="NET" />
                </el-select>
              </el-form-item>
              <el-form-item label="纸宽">
                <el-select v-model="labelPrinter.paperWidth" size="large" class="set-input">
                  <el-option label="58mm" value="58mm" />
                  <el-option label="60mm" value="60mm" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button class="big-btn" @click="testPrint('标签打印机')">
                  <el-icon><Printer /></el-icon>&nbsp;测试打印
                </el-button>
              </el-form-item>
            </el-form>
          </div>
          <!-- 小票打印机 -->
          <div class="printer-block">
            <div class="printer-title">小票打印机（收银小票）</div>
            <el-form label-width="90px" class="set-form">
              <el-form-item label="系统打印机">
                <el-select
                  v-model="receiptPrinter.systemName"
                  size="large"
                  class="set-input"
                  clearable
                  filterable
                  placeholder="未选择（使用浏览器打印）"
                >
                  <el-option v-for="p in systemPrinters" :key="p" :label="p" :value="p" />
                </el-select>
              </el-form-item>
              <el-form-item label="型号">
                <el-input v-model="receiptPrinter.model" size="large" class="set-input" />
              </el-form-item>
              <el-form-item label="端口">
                <el-select v-model="receiptPrinter.port" size="large" class="set-input">
                  <el-option label="USB" value="USB" />
                  <el-option label="串口" value="COM1" />
                  <el-option label="网口" value="NET" />
                </el-select>
              </el-form-item>
              <el-form-item label="纸宽">
                <el-select v-model="receiptPrinter.paperWidth" size="large" class="set-input">
                  <el-option label="58mm" value="58mm" />
                  <el-option label="80mm" value="80mm" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button class="big-btn" @click="testPrint('小票打印机')">
                  <el-icon><Printer /></el-icon>&nbsp;测试打印
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </template>

        <!-- ===== 门店信息 ===== -->
        <template v-else-if="activeMenu === 'store'">
          <div class="panel-title">门店信息</div>
          <el-form label-width="90px" class="set-form">
            <el-form-item label="门店名称">
              <el-input v-model="storeForm.name" size="large" class="set-input" />
            </el-form-item>
            <el-form-item label="联系电话">
              <el-input v-model="storeForm.phone" size="large" class="set-input" />
            </el-form-item>
            <el-form-item label="门店地址">
              <el-input v-model="storeForm.address" size="large" class="set-input" />
            </el-form-item>
            <el-form-item label="小票抬头">
              <el-input v-model="storeForm.receiptHeader" size="large" class="set-input" />
            </el-form-item>
            <el-form-item label="广告语">
              <el-input v-model="storeForm.slogan" size="large" class="set-input" />
            </el-form-item>
          </el-form>
        </template>

        <!-- ===== 同步状态 ===== -->
        <template v-else>
          <div class="panel-title">同步状态</div>
          <!-- 同步状态卡片 -->
          <div class="sync-card">
            <div class="sync-item">
              <div class="sync-label">上次同步时间</div>
              <div class="sync-value num">{{ syncInfo.lastTime }}</div>
            </div>
            <div class="sync-item">
              <div class="sync-label">待上传订单数</div>
              <div class="sync-value num">{{ syncInfo.uploadCount }}</div>
            </div>
            <div class="sync-item">
              <div class="sync-label">待下载商品数</div>
              <div class="sync-value num">{{ syncInfo.downloadCount }}</div>
            </div>
          </div>
          <!-- 立即同步按钮 -->
          <el-button type="primary" class="big-btn sync-btn" @click="doSync">
            <el-icon><Refresh /></el-icon>&nbsp;立即同步
          </el-button>
          <!-- 同步日志表 -->
          <div class="panel-subtitle">同步日志</div>
          <el-table :data="syncLogs" class="log-table">
            <el-table-column prop="time" label="时间" min-width="150">
              <template #default="{ row }"><span class="num">{{ row.time }}</span></template>
            </el-table-column>
            <el-table-column prop="content" label="内容" min-width="240" />
            <el-table-column label="结果" min-width="90">
              <template #default="{ row }">
                <el-tag :type="row.ok ? 'success' : 'danger'" effect="light">{{ row.ok ? '成功' : '失败' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- 底部保存 -->
        <div class="panel-footer">
          <el-button type="primary" class="big-btn save-btn" @click="saveSettings">
            <el-icon><Check /></el-icon>&nbsp;保 存
          </el-button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, Odometer, Printer, Refresh, Shop } from '@element-plus/icons-vue'
import { PrintService } from '../services/print/PrintService'
import { TauriPrintService } from '../services/print/TauriPrintService'

/** 设置项在 localStorage 中的键名 */
const SETTINGS_KEY = 'pos_settings'

// 左侧菜单项与当前选中项
const activeMenu = ref('scale')
const menus = [
  { key: 'scale', label: '称重设置', icon: Odometer },
  { key: 'printer', label: '打印机', icon: Printer },
  { key: 'store', label: '门店信息', icon: Shop },
  { key: 'sync', label: '同步状态', icon: Refresh },
]

// 称重设置表单（模拟数据；connectMode: serial=串口 network=网口 sim=模拟秤）
const scaleForm = reactive({
  connectMode: 'sim',
  comPort: 'COM3',
  baudRate: 9600,
  autoConfirm: true,
  stableCount: 3,
})
const comPorts = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8']
const baudRates = [9600, 4800]

// 打印机配置（随保存写入本地设置；systemName 为系统打印队列名称，空值表示未选择）
const labelPrinter = reactive({ systemName: '', model: '佳博 GP-1224T', port: 'USB', paperWidth: '60mm' })
const receiptPrinter = reactive({ systemName: '', model: '佳博 XP-58III', port: 'USB', paperWidth: '58mm' })

// 打印通道：auto=原生直连优先，html=仅浏览器打印
const printMode = ref('auto')
// 本机系统打印机名称列表
const systemPrinters = ref([])
// 系统打印机列表加载状态
const loadingPrinters = ref(false)
// 原生打印环境提示文案
const nativeTip = ref('')

// 门店信息（默认值取自打印服务，保存后与打印模板保持一致）
const storeForm = reactive({
  name: PrintService.storeInfo.storeName,
  phone: PrintService.storeInfo.phone,
  address: PrintService.storeInfo.storeAddress,
  receiptHeader: PrintService.storeInfo.receiptHeader,
  slogan: PrintService.storeInfo.slogan,
})

// 同步状态（模拟数据）
const syncInfo = reactive({ lastTime: '2026-11-05 09:30', uploadCount: 3, downloadCount: 12 })
const syncLogs = ref([
  { time: '2026-11-05 09:30', content: '上传订单 12 单', ok: true },
  { time: '2026-11-05 09:30', content: '下载商品价格变更 6 条', ok: true },
  { time: '2026-11-05 08:00', content: '上传订单 5 单', ok: true },
  { time: '2026-11-04 20:00', content: '同步收银班次数据', ok: false },
])

/**
 * 加载本机系统打印机列表（浏览器环境返回空列表）
 * @returns {Promise<void>}
 */
const loadSystemPrinters = async () => {
  loadingPrinters.value = true
  try {
    systemPrinters.value = await TauriPrintService.listPrinters()
    if (!TauriPrintService.isAvailable()) {
      nativeTip.value = '当前为浏览器环境，原生直连保存后在桌面客户端生效'
    } else if (!systemPrinters.value.length) {
      nativeTip.value = '未检测到系统打印机，请检查打印机连接与驱动'
    } else {
      nativeTip.value = `已检测到 ${systemPrinters.value.length} 台系统打印机`
    }
  } finally {
    loadingPrinters.value = false
  }
}

// 保存设置：写入 localStorage，并同步门店打印信息与系统打印机选择
const saveSettings = () => {
  const settings = {
    scale: { ...scaleForm },
    labelPrinter: { ...labelPrinter },
    receiptPrinter: { ...receiptPrinter },
    printMode: printMode.value,
    store: { ...storeForm },
  }
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
  PrintService.saveStoreInfo({
    storeName: storeForm.name,
    storeAddress: storeForm.address,
    phone: storeForm.phone,
    receiptHeader: storeForm.receiptHeader,
    slogan: storeForm.slogan,
    paperWidth: parseInt(receiptPrinter.paperWidth, 10) || 58,
    printMode: printMode.value,
    receiptPrinterName: receiptPrinter.systemName || '',
    labelPrinterName: labelPrinter.systemName || '',
  })
  ElMessage.success('设置已保存')
}

/**
 * 组装页面当前表单对应的打印配置（测试打印直接使用，无需先保存）
 * @returns {object} 本次打印生效的打印配置
 */
const buildPrintInfo = () => ({
  storeName: storeForm.name,
  storeAddress: storeForm.address,
  phone: storeForm.phone,
  receiptHeader: storeForm.receiptHeader,
  slogan: storeForm.slogan,
  paperWidth: parseInt(receiptPrinter.paperWidth, 10) || 58,
  printMode: printMode.value,
  receiptPrinterName: receiptPrinter.systemName || '',
  labelPrinterName: labelPrinter.systemName || '',
})

// 测试打印：按打印机类型生成样例，并使用页面当前（未保存）的打印配置
const testPrint = async (name) => {
  const orderNo = `TEST${Date.now()}`
  const info = buildPrintInfo()
  let channel = 'html'
  if (name === '标签打印机') {
    channel = await PrintService.printLabel(
      { orderNo },
      { productId: 1, name: '测试商品', weight: 0.52, price: 9.8, amount: 5.1 },
      info,
    )
  } else {
    channel = await PrintService.printReceipt({
      orderNo,
      cashierName: '测试收银员',
      totalAmount: 12.8,
      discount: 0,
      payMethod: '现金',
      cashReceived: 20,
      change: 7.2,
      items: [
        { name: '测试称重商品', weighted: true, weight: 0.52, price: 9.8, amount: 5.1 },
        { name: '测试按件商品', weighted: false, qty: 1, price: 7.7, amount: 7.7 },
      ],
    }, info)
  }
  if (channel === 'failed') {
    const printerName = name === '标签打印机' ? info.labelPrinterName : info.receiptPrinterName
    ElMessage.error(`测试打印失败：未找到系统打印机「${printerName}」，请刷新打印机列表后重新选择`)
    return
  }
  const channelText = channel === 'native' ? '原生直连' : '浏览器打印'
  ElMessage.success(`测试打印已发送：${name}（${channelText}）`)
}

// 立即同步：更新同步状态并追加日志（演示）
const doSync = () => {
  syncInfo.lastTime = new Date().toLocaleString('zh-CN', { hour12: false })
  syncInfo.uploadCount = 0
  syncInfo.downloadCount = 0
  syncLogs.value.unshift({ time: syncInfo.lastTime, content: '全量同步完成', ok: true })
  ElMessage.success('同步完成，数据已是最新（演示）')
}

// 启动时恢复本地设置；门店信息优先使用打印服务已保存的值
onMounted(() => {
  PrintService.loadStoreInfo()
  Object.assign(storeForm, {
    name: PrintService.storeInfo.storeName,
    phone: PrintService.storeInfo.phone,
    address: PrintService.storeInfo.storeAddress,
    receiptHeader: PrintService.storeInfo.receiptHeader,
    slogan: PrintService.storeInfo.slogan,
  })

  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    const data = raw ? JSON.parse(raw) : null
    if (data) {
      if (data.scale) Object.assign(scaleForm, data.scale)
      if (data.labelPrinter) Object.assign(labelPrinter, data.labelPrinter)
      if (data.receiptPrinter) Object.assign(receiptPrinter, data.receiptPrinter)
      if (data.store) Object.assign(storeForm, data.store)
      if (data.printMode) printMode.value = data.printMode
    }
  } catch {
    ElMessage.warning('本地设置已损坏，已恢复默认值')
  }

  // 打印通道与打印机名称以打印服务已保存的配置为准
  printMode.value = PrintService.storeInfo.printMode || printMode.value
  labelPrinter.systemName = PrintService.storeInfo.labelPrinterName || labelPrinter.systemName
  receiptPrinter.systemName = PrintService.storeInfo.receiptPrinterName || receiptPrinter.systemName
  loadSystemPrinters()
})
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

/* ----- 页面主体：左菜单 + 右内容 ----- */
.page-body {
  flex: 1;
  width: 100%;
  max-width: 1080px;
  margin: 0 auto;
  padding: var(--space-5) var(--space-4);
}
.settings-body {
  display: flex;
  gap: var(--space-4);
  align-items: flex-start;
}

/* 触屏大按钮统一样式 */
.big-btn {
  height: 48px;
  font-size: 17px;
  border-radius: var(--radius-md);
  padding: 0 28px;
}

/* ----- 左侧竖排菜单 ----- */
.side-menu {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fff;
  border-radius: var(--radius-lg);
  border: 1px solid var(--neutral-200);
  box-shadow: var(--shadow-sm);
  padding: var(--space-3);
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  font-size: 16px;
  color: var(--neutral-600);
  cursor: pointer;
  transition: background 0.12s;
}
.menu-item :deep(.el-icon) {
  font-size: 18px;
}
.menu-item:hover:not(.active) {
  background: var(--brand-soft);
  color: var(--brand-deep);
}
.menu-item.active {
  background: var(--brand);
  color: #fff;
  font-weight: 600;
}

/* ----- 右侧内容区 ----- */
.content-card {
  flex: 1;
  background: #fff;
  border-radius: var(--radius-lg);
  border: 1px solid var(--neutral-200);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
  min-height: 620px;
  display: flex;
  flex-direction: column;
}
.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--neutral-900);
  margin-bottom: var(--space-4);
}
.panel-subtitle {
  font-size: 15px;
  font-weight: 600;
  color: var(--neutral-700);
  margin-bottom: var(--space-2);
}

/* ----- 表单 ----- */
.set-form :deep(.el-form-item__label) {
  font-size: 15px;
  color: var(--neutral-600);
}
.set-form :deep(.el-input__wrapper),
.set-form :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: var(--radius-md);
}
.set-input {
  width: 260px;
}
.field-tip {
  margin-left: 12px;
  font-size: 13px;
  color: var(--neutral-400);
}

/* ----- 串口协议说明卡片 ----- */
.proto-card {
  margin-top: var(--space-4);
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}
.proto-title {
  font-weight: 600;
  color: var(--neutral-700);
  margin-bottom: 8px;
}
.proto-card p {
  margin: 4px 0;
  font-size: 13px;
  color: var(--neutral-500);
}

/* ----- 打印机分组 ----- */
.printer-block {
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}
.printer-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--brand-deep);
  margin-bottom: var(--space-3);
}

/* ----- 同步状态 ----- */
.sync-card {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.sync-item {
  flex: 1;
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  text-align: center;
}
.sync-label {
  font-size: 13px;
  color: var(--neutral-400);
  margin-bottom: 6px;
}
.sync-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--neutral-900);
}
.sync-btn {
  margin-bottom: var(--space-4);
}
.log-table :deep(th.el-table__cell) {
  background: var(--neutral-50);
  font-size: 14px;
  color: var(--neutral-600);
}
.log-table :deep(.el-table__row) {
  font-size: 14px;
}

/* ----- 底部保存 ----- */
.panel-footer {
  margin-top: auto;
  padding-top: var(--space-4);
  border-top: 1px solid var(--neutral-200);
  display: flex;
  justify-content: flex-end;
}
.save-btn {
  min-width: 180px;
}
</style>
