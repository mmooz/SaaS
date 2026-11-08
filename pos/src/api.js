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
 * 带 HTTP 状态码的请求异常（Q25：用于区分网络错误与业务错误）
 * 有明确 status 的错误说明服务端已响应，不应无限重试，应进入死信队列。
 */
export class ApiError extends Error {
  /**
   * @param {string} message 错误提示
   * @param {number} status HTTP 状态码
   */
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

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
 * Q26：支持 options.headers 覆盖单次请求的头（如按订单固化门店覆盖 X-Store-Id），
 * 但绝不修改全局「当前门店」缓存，其它请求仍使用原门店上下文。
 * @param {string} path 接口路径
 * @param {object} options fetch 选项（可含 headers）
 * @returns {Promise<any>} 解析后的响应数据
 */
async function request(path, options = {}) {
  const token = getAuthToken()
  const storeId = getCurrentStore()
  const { headers: extraHeaders, ...restOptions } = options
  const res = await fetch(`${BASE_URL}${path}`, {
    ...restOptions,
    headers: {
      'Content-Type': 'application/json',
      // 已登录时自动携带令牌，供后端识别当前用户
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      // 已选门店时携带门店 ID，供后端做门店数据隔离
      ...(storeId ? { 'X-Store-Id': storeId } : {}),
      // 单次覆盖（Q26：离线补传按发生时门店指定）
      ...(extraHeaders || {}),
    },
  })
  // 令牌失效统一处理：清除登录态并回到登录页
  if (res.status === 401 && token) {
    clearAuthToken()
    clearStoreInfo()
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    throw new ApiError('登录已过期，请重新登录', 401)
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    // Q25：把 HTTP status 挂到异常上，供离线队列按错误类型分流
    throw new ApiError(body.detail || `请求失败(${res.status})`, res.status)
  }
  if (res.status === 204) return null
  return res.json()
}

/**
 * 判断请求失败是否属于网络不可用（用于触发离线兜底）
 * Q25：带明确 HTTP status 的异常属于服务端已响应的业务错误（4xx/5xx），
 * 一律返回 false，避免离线队列因脏数据永久卡死；只有 fetch 本身抛出的
 * TypeError / 网络类异常才视为网络错误。
 * @param {Error} err 请求异常
 * @returns {boolean} 是否为网络异常
 */
export function isNetworkError(err) {
  if (!err) return false
  if (typeof err.status === 'number') return false
  if (err instanceof ApiError) return false
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
 * 修改本人登录密码（R19 强制首次改密）
 * 待改密账号的令牌只能调用本接口；成功后旧令牌全部失效，须用新密码重新登录。
 * @param {string} oldPassword 当前密码（弱口令或临时口令均可）
 * @param {string} newPassword 新密码（≥8 位、非弱口令、不得与原密码相同）
 * @returns {Promise<{must_change_password: boolean}>} 改密结果
 */
export function changePassword(oldPassword, newPassword) {
  return request('/api/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  })
}

/**
 * 同步拉取商品/分类/促销/会员（增量同步）
 * Q07/Q19：after 为上次同步返回的 server_time（naive UTC），重启后从本地读取；
 * 载荷含 deleted_ids / disabled_ids tombstone 与全量生效促销、增量会员。
 * @param {string|null} after 上次同步时间（增量）
 * @returns {Promise<object>} { products, categories, deleted_ids, disabled_ids, promotions, members, server_time }
 */
export function fetchSyncData(after = null) {
  const query = after ? `?after=${encodeURIComponent(after)}` : ''
  return request(`/api/sync/products${query}`)
}

/**
 * 上传订单到服务端
 * Q26：按订单载荷中固化的 store_id 覆盖本次请求的 X-Store-Id，
 * 使 A 店离线产生的订单在切到 B 店补传时仍落到 A 店；不修改全局当前门店。
 * @param {object} order 订单数据（含发生时的 store_id）
 * @returns {Promise<object>} 已保存的订单
 */
export function uploadOrder(order) {
  const fixedStoreId =
    order && order.store_id !== null && order.store_id !== undefined && String(order.store_id) !== ''
      ? String(order.store_id)
      : ''
  return request('/api/orders', {
    method: 'POST',
    body: JSON.stringify(order),
    headers: fixedStoreId ? { 'X-Store-Id': fixedStoreId } : {},
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
 * Q17：退款主体由服务端令牌用户决定，不再发送 cashier_id / authorizer_id。
 * 旧客户端仍传这两个字段时服务端会忽略（RefundCreate extra="ignore"），不会返回 422。
 * @param {string} orderNo 订单号
 * @param {object} data 退款数据
 * @param {string} data.refundType full=整单退款 item=单项退货
 * @param {number[]} [data.itemIds] 退货明细主键（单项退货必填）
 * @param {string} [data.reason] 退款原因
 * @param {string} [data.refundNo] 退款单号（离线补传时保留）
 * @param {string} [data.createdAt] 退款时间（离线补传时保留）
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
 * R4：赠送积分由服务端按 rechargeGift 比例换算，不再发送 bonus_points 死字段。
 * @param {number} memberId 会员 ID
 * @param {object} data { amount }
 * @returns {Promise<object>} 更新后的会员信息
 */
export function rechargeMember(memberId, data) {
  return request(`/api/members/${memberId}/recharge`, {
    method: 'POST',
    body: JSON.stringify({ amount: data.amount, gift_amount: data.giftAmount || 0 }),
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
 * Q26：按每条班次快照固化的 store_id 分组，每组用该门店覆盖 X-Store-Id，
 * 既让载荷门店与 Q04 的服务端上下文校验一致，又保证 A 店班次在 B 店补传时
 * 仍落到 A 店；不改全局当前门店。旧快照无 store_id 时归到当前门店组。
 *
 * R13：用 Promise.allSettled 逐组收敛结果，绝不因单个分组失败整体 reject。
 * 调用方按 groups[].ok 判定每个门店的成败，避免已成功上传的分组被一起误伤。
 * @param {Array<object>} shifts 班次快照列表
 * @returns {Promise<{synced:number, groups:Array<{storeId:string, items:Array<object>, ok:boolean, error:Error|null}>}>}
 *   成功分组累计的 synced 与各分组结果（失败时 error 为原始异常，供 isNetworkError 判定）
 */
export function syncShifts(shifts) {
  const groups = new Map()
  for (const shift of shifts || []) {
    const key =
      shift && shift.store_id !== null && shift.store_id !== undefined && String(shift.store_id) !== ''
        ? String(shift.store_id)
        : ''
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(shift)
  }
  const entries = [...groups.entries()]
  if (!entries.length) return Promise.resolve({ synced: 0, groups: [] })
  const tasks = entries.map(([storeId, items]) =>
    request('/api/shifts/sync', {
      method: 'POST',
      body: JSON.stringify({ shifts: items }),
      headers: storeId ? { 'X-Store-Id': storeId } : {},
    }),
  )
  return Promise.allSettled(tasks).then((settled) => {
    let synced = 0
    const results = settled.map((res, index) => {
      const [storeId, items] = entries[index]
      if (res.status === 'fulfilled') {
        synced += Number(res.value && res.value.synced) || 0
        return { storeId, items, ok: true, error: null }
      }
      // 保留原始异常对象（ApiError 带 status / TypeError 网络异常），供调用方分流
      return { storeId, items, ok: false, error: res.reason }
    })
    return { synced, groups: results }
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

/**
 * 把对象转为查询字符串（忽略空值，避免把空串拼进 URL）
 * @param {object} params 查询参数
 * @returns {string} 查询串（含前导 ?）
 */
function query(params = {}) {
  const pairs = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  return pairs.length ? `?${pairs.map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&')}` : ''
}

/**
 * 以表单方式上传文件（Excel 导入用），自动携带令牌与当前门店 ID
 * @param {string} path 接口路径
 * @param {File} file 上传文件
 * @returns {Promise<any>} 解析后的数据
 */
async function upload(path, file) {
  const token = getAuthToken()
  const storeId = getCurrentStore()
  const form = new FormData()
  form.append('file', file)
  const headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  if (storeId) headers['X-Store-Id'] = storeId
  const res = await fetch(`${BASE_URL}${path}`, { method: 'POST', headers, body: form })
  if (res.status === 401 && token) {
    clearAuthToken()
    clearStoreInfo()
    if (window.location.pathname !== '/login') window.location.href = '/login'
    throw new ApiError('登录已过期，请重新登录', 401)
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body.detail || `上传失败(${res.status})`, res.status)
  }
  return res.json()
}

/* ---------------- 分类 ---------------- */

/** 查询当前门店分类树 */
export function fetchCategoryTree() {
  return request('/api/categories/tree')
}
/** 查询分类树（兼容旧调用名） */
export function fetchCategories() {
  return fetchCategoryTree()
}
/** 新增分类 { name, parentId, sort, enabled } */
export function createCategory(data) {
  return request('/api/categories', {
    method: 'POST',
    body: JSON.stringify({
      name: data.name,
      parent_id: data.parentId ?? null,
      sort: data.sort ?? 0,
      enabled: data.enabled ?? true,
    }),
  })
}
/** 更新分类 { name, parentId, sort, enabled } */
export function updateCategory(id, data) {
  return request(`/api/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      name: data.name,
      parent_id: data.parentId ?? null,
      sort: data.sort ?? 0,
      enabled: data.enabled ?? true,
    }),
  })
}
/** 删除分类 */
export function deleteCategory(id) {
  return request(`/api/categories/${id}`, { method: 'DELETE' })
}

/* ---------------- 商品 ---------------- */

/**
 * 分页查询当前门店商品
 * @param {object} params { keyword, categoryId, pricingMode, enabled, page, pageSize }
 */
export function fetchProducts(params = {}) {
  return request(
    `/api/products${query({
      keyword: params.keyword,
      category_id: params.categoryId,
      pricing_mode: params.pricingMode,
      enabled: params.enabled,
      page: params.page,
      page_size: params.pageSize || 200,
    })}`,
  )
}
/** 新增商品（后端字段命名） */
export function createProduct(data) {
  return request('/api/products', { method: 'POST', body: JSON.stringify(data) })
}
/** 更新商品 */
export function updateProduct(id, data) {
  return request(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}
/** 删除商品 */
export function deleteProduct(id) {
  return request(`/api/products/${id}`, { method: 'DELETE' })
}
/** 批量改价 { mode, categoryId, productIds, adjustType, value } */
export function batchAdjustPrice(data) {
  return request('/api/products/batch-price', {
    method: 'POST',
    body: JSON.stringify({
      mode: data.mode,
      category_id: data.categoryId ?? null,
      product_ids: data.productIds || [],
      adjust_type: data.adjustType,
      value: data.value,
    }),
  })
}
/** Excel 导入商品 */
export function importProducts(file) {
  return upload('/api/products/import', file)
}
/** 商品导出地址（浏览器直接下载） */
export function productExportUrl() {
  return `${BASE_URL}/api/products/export`
}
/** 商品导入模板下载地址 */
export function productTemplateUrl() {
  return `${BASE_URL}/api/products/import-template`
}

/* ---------------- 会员 ---------------- */

/** 分页查询本店会员 { keyword, page, pageSize } */
export function fetchMembers(params = {}) {
  return request(`/api/members${query({ keyword: params.keyword, page: params.page, page_size: params.pageSize })}`)
}
/** 更新会员姓名/等级 { name, level } */
export function updateMember(id, data) {
  return request(`/api/members/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}
/** 会员积分调整（正增负减） */
export function adjustPoints(id, points) {
  return request(`/api/members/${id}/points`, { method: 'POST', body: JSON.stringify({ points }) })
}
/** 会员概览统计 */
export function fetchMemberStats() {
  return request('/api/members/stats')
}
/** 分页查询会员流水 { memberId, type, page, pageSize } */
export function fetchMemberTransactions(params = {}) {
  return request(
    `/api/members/transactions/all${query({
      member_id: params.memberId,
      type: params.type,
      page: params.page,
      page_size: params.pageSize,
    })}`,
  )
}

/* ---------------- 促销 ---------------- */

/** 查询当前门店促销列表 { enabled } */
export function fetchPromotions(params = {}) {
  return request(`/api/promotions${query({ enabled: params.enabled })}`)
}
/** 新建促销 */
export function createPromotion(data) {
  return request('/api/promotions', { method: 'POST', body: JSON.stringify(data) })
}
/** 更新促销 */
export function updatePromotion(id, data) {
  return request(`/api/promotions/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}
/** 删除促销 */
export function deletePromotion(id) {
  return request(`/api/promotions/${id}`, { method: 'DELETE' })
}

/* ---------------- 库存 ---------------- */

/** 分页查询当前门店库存 { keyword, categoryId, lowOnly, page, pageSize } */
export function fetchInventory(params = {}) {
  return request(
    `/api/inventory${query({
      keyword: params.keyword,
      category_id: params.categoryId,
      low_only: params.lowOnly,
      page: params.page,
      page_size: params.pageSize,
    })}`,
  )
}
/** 库存预警清单 */
export function fetchInventoryAlerts() {
  return request('/api/inventory/alerts')
}
/** 采购入库 { productId, qty, costPrice } */
export function inventoryInbound(data) {
  return request('/api/inventory/inbound', {
    method: 'POST',
    body: JSON.stringify({ product_id: data.productId, qty: data.qty, cost_price: data.costPrice }),
  })
}
/** 库存盘点 { productId, actual } */
export function inventoryStocktake(data) {
  return request('/api/inventory/stocktake', {
    method: 'POST',
    body: JSON.stringify({ product_id: data.productId, actual: data.actual }),
  })
}
/** 库存报损 { productId, qty } */
export function inventoryBreakage(data) {
  return request('/api/inventory/breakage', {
    method: 'POST',
    body: JSON.stringify({ product_id: data.productId, qty: data.qty }),
  })
}
/** 分页查询库存流水 { productId, type, page, pageSize } */
export function fetchInventoryMovements(params = {}) {
  return request(
    `/api/inventory/movements${query({
      product_id: params.productId,
      type: params.type,
      page: params.page,
      page_size: params.pageSize,
    })}`,
  )
}

/* ---------------- 报表 ---------------- */

/** 销售日报月报 { start, end, mode } */
export function fetchDailyReport(params = {}) {
  return request(`/api/reports/daily${query({ start: params.start, end: params.end, mode: params.mode })}`)
}
/** 商品销售排行 { start, end, limit } */
export function fetchProductRank(params = {}) {
  return request(`/api/reports/products${query({ start: params.start, end: params.end, limit: params.limit })}`)
}
/** 时段分析 { start, end } */
export function fetchHourlyReport(params = {}) {
  return request(`/api/reports/hourly${query({ start: params.start, end: params.end })}`)
}
/** 毛利分析 { start, end } */
export function fetchProfitReport(params = {}) {
  return request(`/api/reports/profit${query({ start: params.start, end: params.end })}`)
}
/** 会员分析 { start, end, limit } */
export function fetchMemberReport(params = {}) {
  return request(`/api/reports/members${query({ start: params.start, end: params.end, limit: params.limit })}`)
}

/* ---------------- 用户（本店员工管理，店长及以上） ---------------- */

/** 分页查询本店可管理用户 { keyword, page, pageSize } */
export function fetchUsers(params = {}) {
  return request(`/api/users${query({ keyword: params.keyword, page: params.page, page_size: params.pageSize })}`)
}
/** 新增用户 { username, name, role, password } */
export function createUser(data) {
  return request('/api/users', {
    method: 'POST',
    body: JSON.stringify({
      username: data.username,
      name: data.name,
      role: data.role,
      password: data.password,
    }),
  })
}
/** 更新用户 { name, role, enabled, password } */
export function updateUser(id, data) {
  return request(`/api/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}
/** 重置密码：服务端生成随机临时密码一次性返回 */
export function resetUserPassword(id) {
  return request(`/api/users/${id}/reset-password`, { method: 'POST' })
}
