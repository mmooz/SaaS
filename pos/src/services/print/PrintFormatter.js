/**
 * 打印格式化工具：统一金额、重量、时间与文本转义，供各打印模板复用。
 */
export class PrintFormatter {
  /**
   * 金额格式化（带 ¥ 符号）
   * @param {number|string} value 金额
   * @returns {string} 例如 ¥12.30
   */
  static money(value) {
    return `¥${(Number(value) || 0).toFixed(2)}`
  }

  /**
   * 金额格式化（不带符号，用于表格右对齐）
   * @param {number|string} value 金额
   * @returns {string} 例如 12.30
   */
  static amount(value) {
    return (Number(value) || 0).toFixed(2)
  }

  /**
   * 重量格式化
   * @param {number|string} value 重量（kg）
   * @returns {string} 例如 0.62kg
   */
  static weight(value) {
    return `${(Number(value) || 0).toFixed(2)}kg`
  }

  /**
   * 时间格式化
   * @param {Date|string|null} value 时间值
   * @returns {string} 例如 2026-11-05 15:20:33
   */
  static datetime(value = new Date()) {
    const d = value instanceof Date ? value : new Date(value)
    if (Number.isNaN(d.getTime())) return ''
    const pad = (n) => String(n).padStart(2, '0')
    return (
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
      `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    )
  }

  /**
   * HTML 文本转义，避免商品名中的特殊字符破坏模板
   * @param {string} text 原始文本
   * @returns {string} 转义后的文本
   */
  static escape(text) {
    return String(text ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }
}
