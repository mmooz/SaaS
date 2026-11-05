/**
 * CODE128 条码编码器：仅使用 Code Set B，支持 ASCII 32~126 字符。
 * 输出模块宽度数据，并可直接生成用于打印的 SVG 条码图形。
 */
export class Code128 {
  /** 起始符 B 的编码值 */
  static START_B = 104

  /** 终止符编码值 */
  static STOP = 106

  /** 静区宽度（模块数），位于条码左右两侧 */
  static QUIET_ZONE = 10

  /**
   * 0~106 的条空模块宽度模式表。
   * 每个字符串 6 位数字（终止符 7 位），奇数位为条、偶数位为空。
   */
  static PATTERNS = [
    '212222', '222122', '222221', '121223', '121322', '131222', '122213', '122312', '132212', '221213',
    '221312', '231212', '112232', '122132', '122231', '113222', '123122', '123221', '223211', '221132',
    '221231', '213212', '223112', '312131', '311222', '321122', '321221', '312212', '322112', '322211',
    '212123', '212321', '232121', '111323', '131123', '131321', '112313', '132113', '132311', '211313',
    '231113', '231311', '112133', '112331', '132131', '113123', '113321', '133121', '313121', '211331',
    '231131', '213113', '213311', '213131', '311123', '311321', '331121', '312113', '312311', '332111',
    '314111', '221411', '431111', '111224', '111422', '121124', '121421', '141122', '141221', '112214',
    '112412', '122114', '122411', '142112', '142211', '241211', '221114', '413111', '241112', '134111',
    '111242', '121142', '121241', '114212', '124112', '124211', '411212', '421112', '421211', '212141',
    '214121', '412121', '111143', '111341', '131141', '114113', '114311', '411113', '411311', '113141',
    '114131', '311141', '411131', '211412', '211214', '211232', '2331112',
  ]

  /**
   * 计算校验位
   * @param {number[]} values 起始符与各数据符的编码值（不含校验位与终止符）
   * @returns {number} 校验值 0~102
   */
  static checksum(values) {
    const sum = values.reduce((acc, value, index) => acc + (index === 0 ? value : value * index), 0)
    return sum % 103
  }

  /**
   * 编码文本为条空模块序列
   * @param {string} text 条码内容（ASCII 32~126）
   * @returns {Array<{ bar: boolean, width: number }>} 模块序列，bar=true 表示黑色条
   * @throws {Error} 内容为空或含不支持的字符时抛出
   */
  static encode(text) {
    const chars = [...String(text ?? '')]
    if (!chars.length) throw new Error('条码内容不能为空')

    const values = [this.START_B]
    chars.forEach((ch) => {
      const code = ch.charCodeAt(0)
      if (code < 32 || code > 126) throw new Error(`CODE128 不支持字符：${ch}`)
      values.push(code - 32)
    })
    values.push(this.checksum(values), this.STOP)

    const modules = []
    values.forEach((value) => {
      const pattern = this.PATTERNS[value]
      for (let i = 0; i < pattern.length; i += 1) {
        modules.push({ bar: i % 2 === 0, width: Number(pattern[i]) })
      }
    })
    return modules
  }

  /**
   * 判断文本是否可被 CODE128 编码
   * @param {string} text 条码内容
   * @returns {boolean} 是否可编码
   */
  static isValid(text) {
    try {
      this.encode(text)
      return true
    } catch {
      return false
    }
  }

  /**
   * 计算条空模块总宽度
   * @param {Array<{ width: number }>} modules 模块序列
   * @returns {number} 总模块数
   */
  static totalWidth(modules) {
    return modules.reduce((sum, module) => sum + module.width, 0)
  }

  /**
   * 生成可打印的条码 SVG
   * @param {string} text 条码内容
   * @param {object} [options] 生成选项
   * @param {number} [options.height] 条码高度（SVG 用户单位），默认 40
   * @param {number} [options.quiet] 左右静区模块数，默认 10
   * @returns {string} SVG 字符串
   * @throws {Error} 文本无法编码时抛出
   */
  static toSvg(text, options = {}) {
    const height = options.height || 40
    const quiet = options.quiet ?? this.QUIET_ZONE
    const modules = this.encode(text)
    const total = this.totalWidth(modules) + quiet * 2

    let x = quiet
    const rects = []
    modules.forEach((module) => {
      if (module.bar) {
        rects.push(`<rect x="${x}" y="0" width="${module.width}" height="${height}"/>`)
      }
      x += module.width
    })

    return `<svg class="barcode-svg" viewBox="0 0 ${total} ${height}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg"><g fill="#000">${rects.join('')}</g></svg>`
  }
}
