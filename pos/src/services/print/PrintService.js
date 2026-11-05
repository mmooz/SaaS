/**
 * 打印服务：优先走 Tauri 原生直连（ESC/POS 小票、TSPL 标签），
 * 未配置打印机或原生失败时回退 HTML 模板 + window.print。
 */
import { ReceiptTemplate } from './ReceiptTemplate.js'
import { LabelTemplate } from './LabelTemplate.js'
import { ShiftTemplate } from './ShiftTemplate.js'
import { TauriPrintService } from './TauriPrintService.js'
import { LabelCode } from './LabelCode.js'
import { PrintFormatter as F } from './PrintFormatter.js'

export class PrintService {
  /** 门店打印信息在 localStorage 中的键名 */
  static STORAGE_KEY = 'pos_store_info'

  /**
   * 打印门店信息（可通过设置页覆盖）
   * @type {{
   *   storeName: string, storeAddress: string, phone: string, receiptHeader: string,
   *   slogan: string, paperWidth: number, printMode: 'auto'|'html',
   *   receiptPrinterName: string, labelPrinterName: string
   * }}
   */
  static storeInfo = {
    storeName: '鲜衡生鲜超市',
    storeAddress: '演示门店 · 生鲜区',
    phone: '0000-0000000',
    receiptHeader: '',
    slogan: '多谢惠顾，欢迎再次光临！',
    paperWidth: 58,
    /** 打印通道：auto=原生优先（未配置则 HTML），html=始终 HTML */
    printMode: 'auto',
    /** 小票打印机（系统打印机名称） */
    receiptPrinterName: '',
    /** 标签打印机（系统打印机名称） */
    labelPrinterName: '',
  }

  /** 允许被空值覆盖的字段（打印机选择需要支持“未选择”） */
  static CLEARABLE_FIELDS = ['receiptPrinterName', 'labelPrinterName', 'printMode']

  /**
   * 从 localStorage 加载门店打印信息（配置损坏时保留默认值）
   * @returns {object} 当前生效的打印信息
   */
  static loadStoreInfo() {
    try {
      const raw = localStorage.getItem(this.STORAGE_KEY)
      if (!raw) return this.storeInfo
      const data = JSON.parse(raw)
      Object.keys(this.storeInfo).forEach((key) => {
        const value = data[key]
        if (value === undefined || value === null) return
        // 打印机名称等字段允许保存为未选择（空字符串），其余字段空值不覆盖默认值
        if (value === '' && !this.CLEARABLE_FIELDS.includes(key)) return
        this.storeInfo[key] = value
      })
    } catch {
      // 配置损坏时忽略，继续使用默认值
    }
    return this.storeInfo
  }

  /**
   * 保存门店打印信息到 localStorage 并立即生效
   * @param {object} info 门店信息（仅合并传入字段）
   * @returns {object} 当前生效的打印信息
   */
  static saveStoreInfo(info) {
    Object.assign(this.storeInfo, info)
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.storeInfo))
    return this.storeInfo
  }

  /**
   * 渲染并调用系统打印
   * @param {string} html 完整 HTML 文档
   * @returns {void}
   */
  static print(html) {
    const iframe = document.createElement('iframe')
    iframe.setAttribute('aria-hidden', 'true')
    iframe.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;'
    document.body.appendChild(iframe)

    const doc = iframe.contentWindow.document
    doc.open()
    doc.write(html)
    doc.close()

    // 等待布局完成后再调起打印，打印结束后移除 iframe
    setTimeout(() => {
      const win = iframe.contentWindow
      win.onafterprint = () => iframe.remove()
      win.focus()
      win.print()
      // 兜底：部分环境不触发 onafterprint，延时回收
      setTimeout(() => {
        if (iframe.parentNode) iframe.remove()
      }, 15000)
    }, 300)
  }

  /**
   * 解析本次打印生效的配置：传入临时配置时优先使用（测试打印无需先保存）
   * @param {object|null} overrideInfo 临时覆盖的打印配置
   * @returns {object} 本次打印生效的打印配置
   */
  static resolveInfo(overrideInfo = null) {
    this.loadStoreInfo()
    if (!overrideInfo) return this.storeInfo
    return { ...this.storeInfo, ...overrideInfo }
  }

  /**
   * 校验系统打印机是否可用：先确认仍然存在，再读取 Win32 状态位
   * @param {string} printerName 目标系统打印机名称
   * @returns {Promise<{ ok: boolean, reason: string }>} 校验结果，不可用时 reason 为提示文案
   */
  static async checkPrinter(printerName) {
    try {
      if (!(await TauriPrintService.hasPrinter(printerName))) {
        return { ok: false, reason: `打印机「${printerName}」不存在或已被移除` }
      }
      const status = await TauriPrintService.printerStatus(printerName)
      if (status && status.usable === false) {
        const problems = Array.isArray(status.problems) && status.problems.length
          ? status.problems.join('、')
          : '状态异常'
        return { ok: false, reason: `打印机「${printerName}」${problems}` }
      }
      return { ok: true, reason: '' }
    } catch (err) {
      // 查询失败时不阻断打印，交由后续原生打印结果决定
      console.warn('校验打印机失败：', err)
      return { ok: true, reason: '' }
    }
  }

  /**
   * 判断是否走原生直连打印
   * @param {string} printerName 目标系统打印机名称
   * @param {string} printMode 打印通道（auto/html），默认取当前配置
   * @returns {boolean} 已选择打印机、未强制 HTML 且处于 Tauri 环境时为 true
   */
  static shouldUseNative(printerName, printMode = this.storeInfo.printMode) {
    if (printMode === 'html') return false
    if (!printerName) return false
    return TauriPrintService.isAvailable()
  }

  /**
   * 组装小票原生打印任务（字段与 Rust ReceiptJob 对应）
   * @param {object} order 小票数据模型
   * @param {object|null} overrideInfo 临时打印配置
   * @returns {object} 原生打印任务
   */
  static buildReceiptJob(order, overrideInfo = null) {
    const info = overrideInfo || this.storeInfo
    const items = (order.items || []).map((item) => {
      const row = {
        name: String(item.name ?? ''),
        weighted: !!item.weighted,
        price: Number(item.price) || 0,
        amount: Number(item.amount) || 0,
      }
      // 称重商品传重量，按件商品传数量（Rust 侧为可选字段）
      if (item.weighted) row.weight = Number(item.weight) || 0
      else row.qty = Number(item.qty) || 0
      return row
    })

    return {
      storeName: info.storeName,
      storeAddress: info.storeAddress,
      phone: info.phone,
      receiptHeader: info.receiptHeader,
      slogan: info.slogan,
      paperWidth: Number(info.paperWidth) || 58,
      orderNo: String(order.orderNo ?? ''),
      time: order.time || F.datetime(),
      cashierName: order.cashierName || '',
      memberMobile: order.memberMobile || '',
      items,
      totalAmount: Number(order.totalAmount) || 0,
      discount: Number(order.discount) || 0,
      payMethod: order.payMethod || '',
      cashReceived: order.cashReceived == null ? null : Number(order.cashReceived),
      change: order.change == null ? null : Number(order.change),
    }
  }

  /**
   * 组装称重标签原生打印任务（字段与 Rust LabelJob 对应）
   * @param {object} order 订单信息（提供单号）
   * @param {Array} items 称重商品列表
   * @param {object|null} overrideInfo 临时打印配置
   * @returns {object} 原生打印任务
   */
  static buildLabelJob(order, items, overrideInfo = null) {
    const info = overrideInfo || this.storeInfo
    return {
      storeName: info.storeName,
      printTime: F.datetime(),
      labels: items.map((item) => ({
        name: String(item.name ?? ''),
        weight: Number(item.weight) || 0,
        price: Number(item.price) || 0,
        amount: Number(item.amount) || 0,
        code: LabelCode.build(order.orderNo, item.productId, item.weight),
      })),
    }
  }

  /**
   * 判断原生打印错误是否由打印机状态问题导致（缺纸/离线/卡纸等）
   * 此类错误应明确提示收银员，而非静默回退 HTML 打印
   * @param {Error} err 原生打印异常
   * @returns {boolean} 是打印机状态问题时为 true
   */
  static isPrinterStatusError(err) {
    const msg = (err && err.message) ? err.message : String(err || '')
    // Rust 层在打印前检测到状态异常时返回「打印机「xxx」缺纸」等文案
    return /打印机「.*」(缺纸|离线|卡纸|已暂停|故障|不可用|需要人工处理|墨粉不足|纸盒门未关闭|出纸仓已满|状态异常)/.test(msg)
  }

  /**
   * 打印小票：原生直连优先，未配置时回退 HTML
   * @param {object} order 小票数据模型（见 ReceiptTemplate）
   * @param {object|null} overrideInfo 临时打印配置（测试打印使用页面当前表单）
   * @returns {Promise<{ channel: 'native'|'html'|'failed', reason: string }>} 实际通道；打印机不可用时为 failed
   */
  static async printReceipt(order, overrideInfo = null) {
    const info = this.resolveInfo(overrideInfo)
    const printerName = info.receiptPrinterName
    if (this.shouldUseNative(printerName, info.printMode)) {
      // 打印机不存在或状态异常时明确失败，不再静默弹浏览器打印框
      const check = await this.checkPrinter(printerName)
      if (!check.ok) return { channel: 'failed', reason: check.reason }
      try {
        await TauriPrintService.printReceipt(printerName, this.buildReceiptJob(order, info))
        return { channel: 'native', reason: '' }
      } catch (err) {
        // 打印机状态问题（缺纸/离线等）直接提示，不回退 HTML
        if (this.isPrinterStatusError(err)) {
          return { channel: 'failed', reason: err.message }
        }
        console.warn('原生打印小票失败，回退 HTML 打印：', err)
      }
    }
    const template = new ReceiptTemplate()
    this.print(template.build(order, info))
    return { channel: 'html', reason: '' }
  }

  /**
   * 打印单张称重标签：原生直连优先，未配置时回退 HTML
   * @param {object} order 订单信息
   * @param {object} item 称重商品
   * @param {object|null} overrideInfo 临时打印配置
   * @returns {Promise<{ channel: 'native'|'html'|'failed', reason: string }>} 实际通道；打印机不可用时为 failed
   */
  static async printLabel(order, item, overrideInfo = null) {
    const info = this.resolveInfo(overrideInfo)
    const printerName = info.labelPrinterName
    if (this.shouldUseNative(printerName, info.printMode)) {
      const check = await this.checkPrinter(printerName)
      if (!check.ok) return { channel: 'failed', reason: check.reason }
      try {
        await TauriPrintService.printLabels(printerName, this.buildLabelJob(order, [item], info))
        return { channel: 'native', reason: '' }
      } catch (err) {
        if (this.isPrinterStatusError(err)) {
          return { channel: 'failed', reason: err.message }
        }
        console.warn('原生打印标签失败，回退 HTML 打印：', err)
      }
    }
    const template = new LabelTemplate()
    this.print(template.build(order, item, info))
    return { channel: 'html', reason: '' }
  }

  /**
   * 打印订单内全部称重商品的标签：原生直连优先，未配置时回退 HTML
   * @param {object} order 订单信息
   * @param {Array} items 称重商品列表，缺省取订单内的称重明细
   * @param {object|null} overrideInfo 临时打印配置
   * @returns {Promise<{ channel: 'native'|'html'|'failed'|'none', count: number, reason: string }>} 实际通道与打印张数
   */
  static async printLabels(order, items, overrideInfo = null) {
    const info = this.resolveInfo(overrideInfo)
    const list = (items || order.items || []).filter((i) => i.weighted)
    if (!list.length) return { channel: 'none', count: 0, reason: '' }
    const printerName = info.labelPrinterName
    if (this.shouldUseNative(printerName, info.printMode)) {
      const check = await this.checkPrinter(printerName)
      if (!check.ok) return { channel: 'failed', count: 0, reason: check.reason }
      try {
        const count = await TauriPrintService.printLabels(
          printerName,
          this.buildLabelJob(order, list, info),
        )
        return { channel: 'native', count: Number(count) || list.length, reason: '' }
      } catch (err) {
        if (this.isPrinterStatusError(err)) {
          return { channel: 'failed', count: 0, reason: err.message }
        }
        console.warn('原生打印标签失败，回退 HTML 打印：', err)
      }
    }
    const template = new LabelTemplate()
    this.print(template.buildMany(order, list, info))
    return { channel: 'html', count: list.length, reason: '' }
  }

  /**
   * 打印交班汇总单
   * @param {object} data 交班数据（见 ShiftTemplate）
   * @returns {void}
   */
  static printShift(data) {
    this.loadStoreInfo()
    const template = new ShiftTemplate()
    this.print(template.build(data, this.storeInfo))
  }
}
