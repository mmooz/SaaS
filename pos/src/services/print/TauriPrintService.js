/**
 * Tauri 原生打印桥接：把打印任务交给 Rust 打印模块，由 Win32 打印队列静默出票。
 * 浏览器环境不存在 Tauri 内部 API，此时全部方法均不可用，由上层回退 HTML 打印。
 */
export class TauriPrintService {
  /**
   * 判断当前是否运行在 Tauri 桌面壳内
   * @returns {boolean} 存在 Tauri invoke 入口时为 true
   */
  static isAvailable() {
    return (
      typeof window !== 'undefined' &&
      !!window.__TAURI_INTERNALS__ &&
      typeof window.__TAURI_INTERNALS__.invoke === 'function'
    )
  }

  /**
   * 调用 Tauri 命令
   * @param {string} command 命令名
   * @param {object} [args] 命令参数（驼峰命名，与 Rust 参数自动转换）
   * @returns {Promise<any>} 命令返回值
   */
  static invoke(command, args = {}) {
    if (!this.isAvailable()) {
      return Promise.reject(new Error('当前环境不支持原生打印'))
    }
    return window.__TAURI_INTERNALS__.invoke(command, args)
  }

  /**
   * 查询当前平台是否支持原生直连打印
   * @returns {Promise<boolean>} 支持情况；非 Tauri 环境返回 false
   */
  static async isSupported() {
    if (!this.isAvailable()) return false
    try {
      return !!(await this.invoke('native_print_supported'))
    } catch {
      return false
    }
  }

  /**
   * 列出本机系统打印机
   * @returns {Promise<string[]>} 打印机名称列表；不可用或失败时返回空数组
   */
  static async listPrinters() {
    if (!this.isAvailable()) return []
    try {
      const list = await this.invoke('list_printers')
      return Array.isArray(list) ? list : []
    } catch {
      return []
    }
  }

  /**
   * 判断系统打印机是否仍然存在
   * @param {string} printerName 系统打印机名称
   * @returns {Promise<boolean>} 存在时为 true；枚举失败时抛出错误
   */
  static async hasPrinter(printerName) {
    const list = await this.invoke('list_printers')
    return Array.isArray(list) && list.includes(printerName)
  }

  /**
   * 原生直连打印小票（ESC/POS）
   * @param {string} printerName 系统打印机名称
   * @param {object} job 小票打印任务（字段与 Rust ReceiptJob 对应）
   * @returns {Promise<void>} 打印成功时 resolve
   */
  static printReceipt(printerName, job) {
    return this.invoke('native_print_receipt', { printerName, job })
  }

  /**
   * 原生直连打印称重标签（TSPL）
   * @param {string} printerName 系统打印机名称
   * @param {object} job 标签打印任务（字段与 Rust LabelJob 对应）
   * @returns {Promise<number>} 实际打印的标签张数
   */
  static printLabels(printerName, job) {
    return this.invoke('native_print_labels', { printerName, job })
  }
}
