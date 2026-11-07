// 设备唯一标识：首次生成后持久化到 localStorage，供两处复用：
// 1) Snowflake.js 用它派生 workerId，避免多台 POS 固定使用同一机器位（Q29）；
// 2) buildOrderNo() 用它作离线单号前缀，避免两台设备同秒同序号生成重复单号（Q26）。
// 重装 / 换机后标识会重新生成，因此不会与历史设备撞号。

// localStorage 键名
const DEVICE_ID_KEY = 'pos_device_id'
// 设备标识长度（8 位十六进制大写字符）
const DEVICE_ID_LENGTH = 8

/**
 * 生成一个新的随机设备标识
 * @returns {string} 8 位十六进制大写字符串
 */
function generateDeviceId() {
  let hex = ''
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    hex = crypto.randomUUID().replace(/-/g, '')
  } else if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(8)
    crypto.getRandomValues(bytes)
    hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
  } else {
    // 极端兜底：非安全上下文下退化使用 Math.random，仅用于本地离线单号去重
    for (let i = 0; i < DEVICE_ID_LENGTH; i += 1) {
      hex += Math.floor(Math.random() * 16).toString(16)
    }
  }
  return hex.slice(0, DEVICE_ID_LENGTH).toUpperCase()
}

/**
 * 读取本设备的稳定标识（首次调用时生成并持久化）
 * @returns {string} 8 位十六进制大写字符串
 */
export function getDeviceId() {
  try {
    const existing = localStorage.getItem(DEVICE_ID_KEY)
    if (existing && existing.length >= DEVICE_ID_LENGTH) return existing
    const generated = generateDeviceId()
    localStorage.setItem(DEVICE_ID_KEY, generated)
    return generated
  } catch {
    // localStorage 被禁用时退化为本次会话内的随机值，不阻断收银
    return generateDeviceId()
  }
}

/**
 * 由设备标识派生雪花 ID 机器位（0-31）
 * 仅用于降低多设备碰撞概率；绝对唯一性由 buildOrderNo() 的完整设备前缀保证
 * @returns {number} 0-31 的机器位
 */
export function getDeviceWorkerId() {
  const id = getDeviceId()
  let hash = 0
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  }
  return hash % 32
}
