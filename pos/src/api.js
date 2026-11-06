// API 请求封装：与后端 FastAPI 服务交互
// 后端地址：开发期为本地 FastAPI 服务

// 后端服务地址：优先读取构建环境变量，缺省回退本地开发地址
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// 登录令牌在 localStorage 中的键名
const TOKEN_KEY = 'pos_token'

// 当前门店 ID 在 localStorage 中的键名
const STORE_KEY = 'pos_store_id'

// 用户可访问的门店列表在 localStorage 中的键名
const STORES_KEY = 'pos_stores'

/**
 * 保存登录令牌（登录成功后调用）
 * @param {string} token 访问令牌
 */
export function setAuthToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 读取本地登录令牌
 * @returns {string} 令牌，未登录时为空字符串
 */
export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

/**
 * 清除本地登录令牌（退出登录时调用）
 */
export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * 保存用户可访问的门店列表（登录成功后调用）
 * @param {Array<{id:string,name:string}>} stores 门店列表
 */
export function setStores(stores) {
  localStorage.setItem(STORES_KEY, JSON.stringify(stores || []))
}

/**
 * 读取用户可访问的门店列表
 * @returns {Array<{id:string,name:string}>} 门店列表
 */
export function getStores() {
  try {
    return JSON.parse(localStorage.getItem(STORES_KEY) || '[]')
  } catch {
    return []
  }
}

/**
 * 设置当前选中的门店 ID
 * @param {string} storeId 门店 ID
 */
export function setCurrentStore(storeId) {
  localStorage.setItem(STORE_KEY, String(storeId))
}

/**
 * 读取当前选中的门店 ID
 * @returns {string} 门店 ID
 */
export function getCurrentStore() {
  return localStorage.getItem(STORE_KEY) || ''
}

/**
 * 清除门店相关本地数据（退出登录时调用）
 */
export function clearStoreInfo() {
  localStorage.removeItem(STORE_KEY)
  localStorage.removeItem(STORES_KEY)
}

/**
 * 发起 JSON 请求
 * @param {string} path 接口路径
 * @param {object} options fetch 选项
 * @returns {Promise<any>} 解析后的响应数据
 */
async function request(path, options = {}) {
  const token = getAuthToken()
  const storeId = getCurrentStore()
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      // 已登录时自动携带令牌，供后端识别当前用户
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      // 已选门店时携带门店 ID，供后端做门店数据隔离
      ...(storeId ? { 'X-Store-Id': storeId } : {}),
    },
    ...options,
  })
  // 令牌失效统一处理：清除登录态并回到登录页
  if (res.status === 401 && token) {
    clearAuthToken()
    clearStoreInfo()
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    throw new Error('登录已过期，请重新登录')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败(${res.status})`)
  }
  if (res.status === 204) return null
  return res.json()
}

/**
 * 判断请求失败是否属于网络不可用（用于触发离线兜底）
 * @param {Error} err 请求异常
 * @returns {boolean} 是否为网络异常
 */
export function isNetworkError(err) {
  if (!err) return false
  if (err instanceof TypeError) return true
  return /failed to fetch|networkerror|network error|load failed|connection/i.test(
    err.message || '',
  )
}

/**
 * 账号密码登录
 * @param {string} username 登录账号（工号）
 * @param {string} password 登录密码
 * @returns {Promise<{access_token:string, token_type:string, expires_in:number, user:object}>} 登录结果
 */
export function login(username, password) {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
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

/**
 * 分页查询订单列表
 * @param {object} [params] 查询参数
 * @param {string} [params.start] 开始时间（ISO）
 * @param {string} [params.end] 结束时间（ISO）
 * @param {string} [params.status] 订单状态
 * @param {number} [params.page] 页码
 * @param {number} [params.pageSize] 每页条数
 * @returns {Promise<{total:number,page:number,page_size:number,items:Array}>}
 */
export function fetchOrders({ start, end, status, keyword, page = 1, pageSize = 20 } = {}) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (start) query.set('start', start)
  if (end) query.set('end', end)
  if (status) query.set('status', status)
  if (keyword) query.set('keyword', keyword)
  return request(`/api/orders?${query.toString()}`)
}

/**
 * 订单退款 / 单项退货
 * @param {string} orderNo 订单号
 * @param {object} data 退款数据
 * @param {string} data.refundType full=整单退款 item=单项退货
 * @param {number[]} [data.itemIds] 退货明细主键（单项退货必填）
 * @param {string} [data.reason] 退款原因
 * @param {string} [data.refundNo] 退款单号（离线补传时保留）
 * @param {string} [data.createdAt] 退款时间（离线补传时保留）
 * @param {number} [data.cashierId] 操作收银员 ID
 * @param {number} [data.authorizerId] 店长授权人 ID
 * @returns {Promise<object>} 退款单
 */
export function refundOrder(orderNo, data) {
  return request(`/api/orders/${encodeURIComponent(orderNo)}/refund`, {
    method: 'POST',
    body: JSON.stringify({
      refund_no: data.refundNo || null,
      created_at: data.createdAt || null,
      refund_type: data.refundType,
      item_ids: data.itemIds || [],
      reason: data.reason || null,
      cashier_id: data.cashierId ?? null,
      authorizer_id: data.authorizerId ?? null,
    }),
  })
}

/**
 * 按订单号查询订单详情（补打小票/标签用）
 * @param {string} orderNo 订单号
 * @returns {Promise<object>} 订单详情（含明细）
 */
export function fetchOrderByNo(orderNo) {
  return request(`/api/orders/${encodeURIComponent(orderNo)}`)
}

/**
 * 拉取当前生效的促销规则（收银端规则引擎使用）
 * @returns {Promise<Array<object>>} 生效促销列表
 */
export function fetchActivePromotions() {
  return request('/api/promotions/active')
}

/**
 * 按手机号查询会员（收银端会员识别）
 * @param {string} mobile 会员手机号
 * @returns {Promise<object>} 会员信息
 */
export function fetchMemberByMobile(mobile) {
  return request(`/api/members/${encodeURIComponent(mobile)}`)
}

/**
 * 新建会员档案
 * @param {object} data { mobile, name }
 * @returns {Promise<object>} 新建的会员信息
 */
export function createMember(data) {
  return request('/api/members', { method: 'POST', body: JSON.stringify(data) })
}

/**
 * 会员储值充值
 * @param {number} memberId 会员 ID
 * @param {object} data { amount, bonusPoints }
 * @returns {Promise<object>} 更新后的会员信息
 */
export function rechargeMember(memberId, data) {
  return request(`/api/members/${memberId}/recharge`, {
    method: 'POST',
    body: JSON.stringify({ amount: data.amount, bonus_points: data.bonusPoints || 0 }),
  })
}

/**
 * 会员储值消费扣款（同时累计积分）
 * @param {number} memberId 会员 ID
 * @param {object} data { amount, orderNo }
 * @returns {Promise<object>} 更新后的会员信息
 */
export function consumeMember(memberId, data) {
  return request(`/api/members/${memberId}/consume`, {
    method: 'POST',
    body: JSON.stringify({ amount: data.amount, order_no: data.orderNo || null }),
  })
}

/**
 * 接班开班
 * @param {object} data { cashierId, baseCash }
 * @returns {Promise<object>} 进行中的班次
 */
export function openShift(data) {
  return request('/api/shifts/open', {
    method: 'POST',
    body: JSON.stringify({ cashier_id: data.cashierId, base_cash: data.baseCash ?? 0 }),
  })
}

/**
 * 查询收银员当前进行中的班次
 * @param {number} cashierId 收银员用户 ID
 * @returns {Promise<object|null>} 班次或 null
 */
export function fetchCurrentShift(cashierId) {
  return request(`/api/shifts/current?cashier_id=${encodeURIComponent(cashierId)}`)
}

/**
 * 查询班次汇总
 * @param {number} shiftId 班次 ID
 * @returns {Promise<object>} 汇总数据
 */
export function fetchShiftSummary(shiftId) {
  return request(`/api/shifts/${encodeURIComponent(shiftId)}/summary`)
}

/**
 * 批量补传离线班次
 * @param {Array<object>} shifts 班次快照列表
 * @returns {Promise<{synced:number}>} 处理结果
 */
export function syncShifts(shifts) {
  return request('/api/shifts/sync', {
    method: 'POST',
    body: JSON.stringify({ shifts }),
  })
}

/**
 * 交班
 * @param {number} shiftId 班次 ID
 * @param {object} data { actualCash, remark }
 * @returns {Promise<object>} 交班后的班次汇总
 */
export function closeShift(shiftId, data = {}) {
  return request(`/api/shifts/${encodeURIComponent(shiftId)}/close`, {
    method: 'POST',
    body: JSON.stringify({
      actual_cash: data.actualCash ?? null,
      remark: data.remark || null,
    }),
  })
}
