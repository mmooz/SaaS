/**
 * 称重标签码编解码：15 位数字，依次为订单号后 8 位 + 商品 ID 3 位 + 重量 4 位（单位 0.01kg）。
 * 打印标签与扫码入车共用同一规则，保证编码与解析一致。
 */
export class LabelCode {
  /** 订单号片段位数 */
  static ORDER_DIGITS = 8

  /** 商品 ID 位数 */
  static PRODUCT_DIGITS = 3

  /** 重量片段位数（单位 0.01kg） */
  static WEIGHT_DIGITS = 4

  /** 标签码总长度 */
  static TOTAL_LENGTH = 15

  /**
   * 生成 15 位标签码
   * @param {string} orderNo 订单号
   * @param {number} productId 商品 ID
   * @param {number} weight 重量（kg）
   * @returns {string} 15 位数字标签码
   */
  static build(orderNo, productId, weight) {
    const orderPart = String(orderNo || '').replace(/\D/g, '').slice(-this.ORDER_DIGITS).padStart(this.ORDER_DIGITS, '0')
    const productPart = String(Math.max(0, Number(productId) || 0)).padStart(this.PRODUCT_DIGITS, '0').slice(-this.PRODUCT_DIGITS)
    const weightPart = String(Math.round((Number(weight) || 0) * 100)).padStart(this.WEIGHT_DIGITS, '0').slice(-this.WEIGHT_DIGITS)
    return `${orderPart}${productPart}${weightPart}`
  }

  /**
   * 解析 15 位标签码
   * @param {string} code 扫描得到的标签码
   * @returns {{ productId: number, weight: number }|null} 解析结果，格式不合法返回 null
   */
  static parse(code) {
    const text = String(code || '').trim()
    if (!new RegExp(`^\\d{${this.TOTAL_LENGTH}}$`).test(text)) return null

    const start = this.ORDER_DIGITS
    const productId = Number(text.slice(start, start + this.PRODUCT_DIGITS))
    const weight = Number(text.slice(start + this.PRODUCT_DIGITS, this.TOTAL_LENGTH)) / 100
    return { productId, weight }
  }
}
