/**
 * 称重标签模板：生成 40mm×30mm 价格标签的完整 HTML 文档。
 */
import { PrintFormatter as F } from './PrintFormatter.js'
import { Code128 } from './Code128.js'

export class LabelTemplate {
  /**
   * 生成单张标签 HTML
   * @param {object} order 订单信息（提供单号与时间）
   * @param {object} item 称重商品明细 { name, weight, price, amount, productId }
   * @param {object} [options] 打印选项
   * @param {string} [options.storeName] 门店名称
   * @param {Date} [options.printTime] 打印时间，默认当前时间
   * @returns {string} 可打印的完整 HTML
   */
  build(order, item, options = {}) {
    const storeName = options.storeName || '鲜衡生鲜超市'
    const printTime = F.datetime(options.printTime || new Date())
    const code = this.buildCode(order, item)

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>标签 ${F.escape(item.name)}</title>
<style>
  @page { size: 40mm 30mm; margin: 1mm; }
  * { box-sizing: border-box; }
  body {
    width: 38mm; height: 28mm; margin: 0; color: #000; overflow: hidden;
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  }
  .store { font-size: 9px; text-align: center; letter-spacing: 1px; }
  .name {
    font-size: 13px; font-weight: 700; text-align: center; line-height: 16px;
    margin-top: 1px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
  }
  .weight { font-size: 15px; font-weight: 700; text-align: center; line-height: 18px; }
  .price { display: flex; justify-content: space-between; font-size: 9px; }
  .amount { display: flex; justify-content: space-between; font-size: 11px; font-weight: 700; }
  .barcode { height: 12px; margin-top: 2px; }
  .barcode svg { display: block; width: 100%; height: 100%; }
  .code-text { text-align: center; font-size: 7px; letter-spacing: 1px; }
  .time { text-align: center; font-size: 7px; }
</style>
</head>
<body>
  <div class="store">${F.escape(storeName)}</div>
  <div class="name">${F.escape(item.name)}</div>
  <div class="weight">${F.amount(item.weight)} kg</div>
  <div class="price">
    <span>单价 ${F.money(item.price)}/kg</span>
    <span>金额 ${F.money(item.amount)}</span>
  </div>
  <div class="barcode">${this.barcode(code)}</div>
  <div class="code-text">${F.escape(code)}</div>
  <div class="time">${F.escape(printTime)}</div>
</body>
</html>`
  }

  /**
   * 生成多张标签合并的 HTML（每张单独一页）
   * @param {object} order 订单信息
   * @param {Array} items 称重商品列表
   * @param {object} [options] 打印选项
   * @returns {string} 可打印的完整 HTML
   */
  buildMany(order, items, options = {}) {
    const storeName = options.storeName || '鲜衡生鲜超市'
    const printTime = F.datetime(options.printTime || new Date())

    // 每张标签独立分页
    const pages = (items || []).map((item) => {
      const code = this.buildCode(order, item)
      return `<div class="label-page">
        <div class="store">${F.escape(storeName)}</div>
        <div class="name">${F.escape(item.name)}</div>
        <div class="weight">${F.amount(item.weight)} kg</div>
        <div class="price">
          <span>单价 ${F.money(item.price)}/kg</span>
          <span>金额 ${F.money(item.amount)}</span>
        </div>
        <div class="barcode">${this.barcode(code)}</div>
        <div class="code-text">${F.escape(code)}</div>
        <div class="time">${F.escape(printTime)}</div>
      </div>`
    }).join('')

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>称重标签</title>
<style>
  @page { size: 40mm 30mm; margin: 1mm; }
  * { box-sizing: border-box; }
  body { margin: 0; color: #000; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
  .label-page {
    width: 38mm; height: 28mm; overflow: hidden;
    page-break-after: always; break-after: page;
  }
  .label-page:last-child { page-break-after: auto; break-after: auto; }
  .store { font-size: 9px; text-align: center; letter-spacing: 1px; }
  .name {
    font-size: 13px; font-weight: 700; text-align: center; line-height: 16px; margin-top: 1px;
    overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
  }
  .weight { font-size: 15px; font-weight: 700; text-align: center; line-height: 18px; }
  .price { display: flex; justify-content: space-between; font-size: 9px; }
  .barcode { height: 12px; margin-top: 2px; }
  .barcode svg { display: block; width: 100%; height: 100%; }
  .code-text { text-align: center; font-size: 7px; letter-spacing: 1px; }
  .time { text-align: center; font-size: 7px; }
</style>
</head>
<body>${pages}</body>
</html>`
  }

  /**
   * 生成标签条码内容（订单号片段 + 商品 ID + 重量编码）
   * @param {object} order 订单信息
   * @param {object} item 称重商品
   * @returns {string} 条码字符串
   */
  buildCode(order, item) {
    const digits = String(order.orderNo || '').replace(/\D/g, '').slice(-8)
    const productPart = String(item.productId ?? 0).padStart(3, '0')
    const weightPart = String(Math.round(Number(item.weight) * 100)).padStart(4, '0')
    return `${digits}${productPart}${weightPart}`
  }

  /**
   * 生成 CODE128 条码 SVG 图形
   * @param {string} text 条码内容
   * @returns {string} 条码 SVG，内容不可编码时返回空字符串
   */
  barcode(text) {
    if (!Code128.isValid(text)) return ''
    return Code128.toSvg(text, { height: 40 })
  }
}
