/**
 * 小票模板：生成 58mm / 80mm 热敏小票的完整 HTML 文档。
 */
import { PrintFormatter as F } from './PrintFormatter.js'
import { Code128 } from './Code128.js'

export class ReceiptTemplate {
  /**
   * 生成小票 HTML
   * @param {object} order 小票数据模型
   * @param {string} order.orderNo 订单号
   * @param {string} order.time 交易时间
   * @param {string} order.cashierName 收银员
   * @param {Array} order.items 商品明细 [{ name, weighted, weight, qty, price, amount }]
   * @param {number} order.totalAmount 应收合计
   * @param {number} [order.discount] 优惠金额
   * @param {string} [order.payMethod] 支付方式
   * @param {number} [order.cashReceived] 实收现金（仅现金支付）
   * @param {number} [order.change] 找零
   * @param {string} [order.memberMobile] 会员手机号
   * @param {object} [options] 打印选项
   * @param {number} [options.paperWidth] 纸宽（mm），默认 58
   * @param {string} [options.storeName] 门店名称
   * @param {string} [options.storeAddress] 门店地址
   * @param {string} [options.phone] 联系电话
   * @param {string} [options.receiptHeader] 小票抬头（抬头行下方展示）
   * @param {string} [options.slogan] 广告语（小票页脚展示）
   * @returns {string} 可打印的完整 HTML
   */
  build(order, options = {}) {
    const paperWidth = options.paperWidth || 58
    const storeName = options.storeName || '鲜衡生鲜超市'
    const storeAddress = options.storeAddress || '演示门店 · 生鲜区'
    const phone = options.phone || ''
    const receiptHeader = options.receiptHeader || ''
    const slogan = options.slogan || '多谢惠顾，欢迎再次光临！'
    const discount = Number(order.discount) || 0
    const total = Number(order.totalAmount) || 0
    const payable = Math.max(0, total - discount)

    // 商品明细行
    const itemRows = (order.items || []).map((item) => {
      const qtyText = item.weighted
        ? `${F.weight(item.weight)} × ${F.amount(item.price)}`
        : `${item.qty} × ${F.amount(item.price)}`
      return `
        <div class="item">
          <div class="item-name">${F.escape(item.name)}</div>
          <div class="item-line"><span>${qtyText}</span><span>${F.amount(item.amount)}</span></div>
        </div>`
    }).join('')

    // 现金支付的实收与找零
    const cashRows = order.payMethod === '现金' && order.cashReceived != null
      ? `<div class="row"><span>实收</span><span>${F.amount(order.cashReceived)}</span></div>
         <div class="row"><span>找零</span><span>${F.amount(order.change)}</span></div>`
      : ''

    // 会员信息行
    const memberRow = order.memberMobile
      ? `<div class="row"><span>会员手机</span><span>${F.escape(order.memberMobile)}</span></div>`
      : ''

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>小票 ${F.escape(order.orderNo)}</title>
<style>
  @page { size: ${paperWidth}mm auto; margin: 2mm; }
  * { box-sizing: border-box; }
  body {
    width: ${paperWidth - 4}mm; margin: 0; color: #000;
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif; font-size: 11px;
  }
  .center { text-align: center; }
  .store-name { font-size: 15px; font-weight: 700; letter-spacing: 1px; }
  .store-sub { font-size: 10px; margin-top: 2px; }
  .divider { border-top: 1px dashed #000; margin: 4px 0; }
  .meta div { display: flex; justify-content: space-between; line-height: 16px; }
  .head { display: flex; justify-content: space-between; font-weight: 700; }
  .item { margin: 2px 0; }
  .item-name { line-height: 15px; }
  .item-line { display: flex; justify-content: space-between; font-size: 10px; }
  .row { display: flex; justify-content: space-between; line-height: 16px; }
  .row.total { font-size: 13px; font-weight: 700; }
  .barcode { height: 30px; margin-top: 6px; }
  .barcode svg { display: block; width: 100%; height: 100%; }
  .code-text { text-align: center; font-size: 10px; letter-spacing: 1px; margin-top: 2px; }
  .footer { text-align: center; font-size: 10px; margin-top: 6px; }
</style>
</head>
<body>
  <div class="center">
    <div class="store-name">${F.escape(storeName)}</div>
    <div class="store-sub">${F.escape(storeAddress)}${phone ? ` · ${F.escape(phone)}` : ''}</div>
    ${receiptHeader ? `<div class="store-sub">${F.escape(receiptHeader)}</div>` : ''}
  </div>

  <div class="divider"></div>

  <div class="meta">
    <div><span>单号</span><span>${F.escape(order.orderNo)}</span></div>
    <div><span>时间</span><span>${F.escape(order.time || F.datetime())}</span></div>
    <div><span>收银员</span><span>${F.escape(order.cashierName || '—')}</span></div>
    ${memberRow}
  </div>

  <div class="divider"></div>
  <div class="head"><span>品名 / 数量</span><span>金额</span></div>
  <div class="divider"></div>
  ${itemRows || '<div class="item"><div class="item-name">（无商品）</div></div>'}
  <div class="divider"></div>

  <div class="row"><span>商品件数</span><span>${(order.items || []).length}</span></div>
  <div class="row"><span>合计</span><span>${F.amount(total)}</span></div>
  ${discount > 0 ? `<div class="row"><span>优惠</span><span>-${F.amount(discount)}</span></div>` : ''}
  <div class="row total"><span>应收</span><span>${F.money(payable)}</span></div>
  ${order.payMethod ? `<div class="row"><span>${F.escape(order.payMethod)}</span><span>${F.amount(payable)}</span></div>` : ''}
  ${cashRows}

  <div class="divider"></div>
  <div class="barcode">${this.barcode(order.orderNo)}</div>
  <div class="code-text">${F.escape(order.orderNo)}</div>
  <div class="footer">${F.escape(slogan)}</div>
</body>
</html>`
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
