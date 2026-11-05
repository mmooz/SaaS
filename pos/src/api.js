// API 请求封装：与后端 FastAPI 服务交互
// 后端地址：开发期为本地 FastAPI 服务

const BASE_URL = 'http://127.0.0.1:8000'

/**
 * 发起 JSON 请求
 * @param {string} path 接口路径
 * @param {object} options fetch 选项
 * @returns {Promise<any>} 解析后的响应数据
 */
async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败(${res.status})`)
  }
  if (res.status === 204) return null
  return res.json()
}

/**
 * 同步拉取商品与分类（增量同步）
 * @param {string|null} after 上次同步时间（增量）
 * @returns {Promise<object>} { products, categories }
 */
export function fetchSyncData(after = null) {
  const query = after ? `?after=${encodeURIComponent(after)}` : ''
  return request(`/api/sync/products${query}`)
}

/**
 * 上传订单到服务端
 * @param {object} order 订单数据
 * @returns {Promise<object>} 已保存的订单
 */
export function uploadOrder(order) {
  return request('/api/orders', {
    method: 'POST',
    body: JSON.stringify(order),
  })
}

/**
 * 查询服务端健康状态
 * @returns {Promise<object>}
 */
export function fetchHealth() {
  return request('/api/health')
}
