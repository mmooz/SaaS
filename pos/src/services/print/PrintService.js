/**
 * 打印服务：把模板生成的 HTML 送入系统打印通道（隐藏 iframe + window.print）。
 * 浏览器与 Tauri WebView 共用同一实现。
 */
import { ReceiptTemplate } from './ReceiptTemplate.js'
import { LabelTemplate } from './LabelTemplate.js'
import { ShiftTemplate } from './ShiftTemplate.js'

export class PrintService {
  /**
   * 打印门店信息（可通过设置页覆盖）
   * @type {{ storeName: string, storeAddress: string, phone: string, paperWidth: number }}
   */
  static storeInfo = {
    storeName: '鲜衡生鲜超市',
    storeAddress: '演示门店 · 生鲜区',
    phone: '0000-0000000',
    paperWidth: 58,
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
   * 打印小票
   * @param {object} order 小票数据模型（见 ReceiptTemplate）
   * @returns {void}
   */
  static printReceipt(order) {
    const template = new ReceiptTemplate()
    this.print(template.build(order, this.storeInfo))
  }

  /**
   * 打印单张称重标签
   * @param {object} order 订单信息
   * @param {object} item 称重商品
   * @returns {void}
   */
  static printLabel(order, item) {
    const template = new LabelTemplate()
    this.print(template.build(order, item, this.storeInfo))
  }

  /**
   * 打印订单内全部称重商品的标签
   * @param {object} order 订单信息
   * @param {Array} items 称重商品列表，缺省取订单内的称重明细
   * @returns {number} 实际打印的标签数量
   */
  static printLabels(order, items) {
    const list = (items || order.items || []).filter((i) => i.weighted)
    if (!list.length) return 0
    const template = new LabelTemplate()
    this.print(template.buildMany(order, list, this.storeInfo))
    return list.length
  }

  /**
   * 打印交班汇总单
   * @param {object} data 交班数据（见 ShiftTemplate）
   * @returns {void}
   */
  static printShift(data) {
    const template = new ShiftTemplate()
    this.print(template.build(data, this.storeInfo))
  }
}
