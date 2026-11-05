/**
 * Tauri 原生电子秤桥接：把称重命令交给 Rust 秤模块（串口/网口/模拟秤）。
 * 浏览器环境不存在 Tauri 内部 API，此时由收银端降级为本地模拟称重。
 */
export class TauriScaleService {
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
   * @param {object} [args] 命令参数
   * @returns {Promise<any>} 命令返回值
   */
  static invoke(command, args = {}) {
    if (!this.isAvailable()) {
      return Promise.reject(new Error('当前环境不支持原生称重'))
    }
    return window.__TAURI_INTERNALS__.invoke(command, args)
  }

  /**
   * 连接电子秤
   * @param {object} options 连接参数
   * @param {string} options.connection 连接方式：mock/serial/tcp
   * @param {string} [options.portName] 串口名称
   * @param {number} [options.baudRate] 波特率
   * @param {string} [options.tcpAddr] 网口地址 ip:port
   * @returns {Promise<string>} 连接结果描述
   */
  static connect({ connection, portName, baudRate, tcpAddr } = {}) {
    return this.invoke('connect_scale', {
      connection,
      portName: portName || null,
      baudRate: baudRate || null,
      tcpAddr: tcpAddr || null,
    })
  }

  /**
   * 读取当前重量（kg，已扣去皮）
   * @returns {Promise<number>} 重量
   */
  static readWeight() {
    return this.invoke('read_scale_weight')
  }

  /**
   * 去皮
   * @returns {Promise<void>}
   */
  static tare() {
    return this.invoke('scale_tare')
  }

  /**
   * 置零
   * @returns {Promise<void>}
   */
  static zero() {
    return this.invoke('scale_zero')
  }

  /**
   * 查询秤连接状态
   * @returns {Promise<boolean>} 已连接为 true
   */
  static isConnected() {
    return this.invoke('scale_connected')
  }
}
