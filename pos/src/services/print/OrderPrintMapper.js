/**
 * 订单打印模型映射：把服务端订单结构转换为打印模板所需的统一结构。
 */
import { PrintFormatter as F } from './PrintFormatter.js'

export class OrderPrintMapper {
  /**
   * 服务端订单（OrderOut）转打印模型
   * @param {object} order 服务端订单
   * @returns {object} 打印模型（ReceiptTemplate / LabelTemplate 可直接使用）
   */
  static fromServer(order) {
    return {
      orderNo: order.order_no,
      time: F.datetime(order.created_at),
      cashierName: order.cashier_id ? `#${order.cashier_id}` : '—',
      totalAmount: order.total_amount,
      discount: order.discount_amount || 0,
      payMethod: this.payMethod(order.pay_details),
      memberMobile: order.member_id ? `会员#${order.member_id}` : '',
      items: (order.items || []).map((item) => ({
        productId: item.product_id,
        name: item.name,
        weighted: !!item.is_weighted,
        weight: item.weight_kg || 0,
        qty: item.qty,
        price: item.unit_price,
        amount: item.amount,
      })),
    }
  }

  /**
   * 本地购物车 + 结算结果转打印模型（收银台即时打印用）
   * @param {object} result 结算结果 { orderNo, order }
   * @param {object} meta 结算附加信息 { cashierName, payMethod, cashReceived, change, memberMobile }
   * @returns {object} 打印模型
   */
  static fromSettle(result, meta = {}) {
    const order = result.order
    const items = (order.items || []).map((item) => ({
      productId: item.product_id,
      name: item.name,
      weighted: !!item.is_weighted,
      weight: item.weight_kg || 0,
      qty: item.qty,
      price: item.unit_price,
      amount: item.amount,
    }))
    return {
      orderNo: result.orderNo,
      time: F.datetime(),
      cashierName: meta.cashierName || '',
      totalAmount: order.total_amount,
      discount: order.discount_amount || 0,
      payMethod: meta.payMethod || '',
      cashReceived: meta.cashReceived,
      change: meta.change,
      memberMobile: meta.memberMobile || '',
      items,
    }
  }

  /**
   * 解析支付方式明细（JSON 字符串形如 {"现金": 12.3}）
   * @param {string|null} payDetails 支付明细
   * @returns {string} 支付方式名称
   */
  static payMethod(payDetails) {
    try {
      const parsed = JSON.parse(payDetails || '{}')
      const keys = Object.keys(parsed)
      return keys.length ? keys[0] : ''
    } catch {
      return ''
    }
  }
}
