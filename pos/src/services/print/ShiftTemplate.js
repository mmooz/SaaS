/**
 * 交班汇总单模板：生成交班小票的完整 HTML 文档（80mm 热敏纸）。
 */
import { PrintFormatter as F } from './PrintFormatter.js'

export class ShiftTemplate {
  /**
   * 生成交班汇总单 HTML
   * @param {object} data 交班数据
   * @param {string} data.cashierName 收银员
   * @param {string} data.shiftName 班次名称
   * @param {string} data.startTime 开班时间
   * @param {string} data.endTime 交班时间
   * @param {number} data.orderCount 订单数
   * @param {number} data.totalAmount 销售合计
   * @param {Array} data.payments 支付方式汇总 [{ method, amount, count }]
   * @param {number} [data.refundAmount] 退款金额
   * @param {number} [data.openingCash] 备用金
   * @param {number} [data.cashShould] 应有现金
   * @param {object} [options] 打印选项
   * @param {string} [options.storeName] 门店名称
   * @returns {string} 可打印的完整 HTML
   */
  build(data, options = {}) {
    const storeName = options.storeName || '鲜衡生鲜超市'
    const payments = data.payments || []

    // 支付方式明细行
    const payRows = payments
      .map((p) => `<div class="row"><span>${F.escape(p.method)}（${p.count || 0}笔）</span><span>${F.amount(p.amount)}</span></div>`)
      .join('')

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>交班汇总单</title>
<style>
  @page { size: 80mm auto; margin: 3mm; }
  * { box-sizing: border-box; }
  body {
    width: 74mm; margin: 0; color: #000;
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif; font-size: 12px;
  }
  .center { text-align: center; }
  .title { font-size: 17px; font-weight: 700; letter-spacing: 2px; }
  .store { font-size: 11px; color: #333; margin-top: 2px; }
  .divider { border-top: 1px dashed #000; margin: 6px 0; }
  .row { display: flex; justify-content: space-between; line-height: 20px; }
  .row.strong { font-size: 15px; font-weight: 700; }
  .section-title { font-weight: 700; margin: 6px 0 2px; }
  .footer { text-align: center; font-size: 10px; margin-top: 8px; }
</style>
</head>
<body>
  <div class="center">
    <div class="store">${F.escape(storeName)}</div>
    <div class="title">交 班 汇 总 单</div>
  </div>

  <div class="divider"></div>

  <div class="row"><span>收银员</span><span>${F.escape(data.cashierName || '—')}</span></div>
  <div class="row"><span>班次</span><span>${F.escape(data.shiftName || '—')}</span></div>
  <div class="row"><span>开班时间</span><span>${F.escape(data.startTime || '—')}</span></div>
  <div class="row"><span>交班时间</span><span>${F.escape(data.endTime || F.datetime())}</span></div>

  <div class="divider"></div>

  <div class="row"><span>订单数</span><span>${data.orderCount || 0} 笔</span></div>
  <div class="row strong"><span>销售合计</span><span>${F.money(data.totalAmount)}</span></div>
  ${data.refundAmount ? `<div class="row"><span>退款金额</span><span>-${F.amount(data.refundAmount)}</span></div>` : ''}

  <div class="divider"></div>
  <div class="section-title">支付方式明细</div>
  ${payRows || '<div class="row"><span>无</span><span>0.00</span></div>'}

  <div class="divider"></div>
  <div class="row"><span>备用金</span><span>${F.amount(data.openingCash)}</span></div>
  <div class="row strong"><span>应有现金</span><span>${F.money(data.cashShould)}</span></div>

  <div class="divider"></div>
  <div class="row"><span>收银员签字</span><span>__________</span></div>
  <div class="row"><span>核对方签字</span><span>__________</span></div>

  <div class="footer">本单由鲜衡 POS 自动生成 · ${F.datetime()}</div>
</body>
</html>`
  }
}
