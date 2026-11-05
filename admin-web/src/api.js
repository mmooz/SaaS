// 后台管理 API 封装：统一请求后端 FastAPI 服务

const BASE_URL = 'http://127.0.0.1:8000'
// 后台登录令牌缓存键
const TOKEN_KEY = 'admin_token'

/**
 * 保存后台登录令牌
 * @param {string} token 访问令牌
 */
export function setAdminToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 读取后台登录令牌
 * @returns {string} 令牌（不存在时为空串）
 */
export function getAdminToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

/**
 * 清除后台登录令牌
 */
export function clearAdminToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * 后台登录
 * @param {string} username 用户名
 * @param {string} password 密码
 * @returns {Promise<object>} { access_token, user }
 */
export function login(username, password) {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

/**
 * 发起 JSON 请求并解析响应
 * @param {string} path 接口路径
 * @param {object} options fetch 选项
 * @returns {Promise<any>} 解析后的数据
 */
async function request(path, options = {}) {
  const token = getAdminToken()
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败(${res.status})`)
  }
  if (res.status === 204) return null
  return res.json()
}

/**
 * 以表单方式上传文件（Excel 导入用）
 * @param {string} path 接口路径
 * @param {File} file 上传文件
 * @returns {Promise<any>} 解析后的数据
 */
async function upload(path, file) {
  const token = getAdminToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `上传失败(${res.status})`)
  }
  return res.json()
}

/**
 * 把对象转为查询字符串（忽略空值）
 * @param {object} params 查询参数
 * @returns {string} 查询串（含前导 ?）
 */
function query(params = {}) {
  const pairs = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  return pairs.length ? `?${pairs.map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&')}` : ''
}

/* ---------------- 会员 ---------------- */

/**
 * 分页查询会员
 * @param {object} params { keyword, page, pageSize }
 * @returns {Promise<object>} 会员分页数据
 */
export function fetchMembers(params = {}) {
  return request(`/api/members${query({ keyword: params.keyword, page: params.page, page_size: params.pageSize })}`)
}

/**
 * 新建会员
 * @param {object} data { mobile, name, level }
 * @returns {Promise<object>} 会员信息
 */
export function createMember(data) {
  return request('/api/members', { method: 'POST', body: JSON.stringify(data) })
}

/**
 * 更新会员姓名/等级
 * @param {number} id 会员 ID
 * @param {object} data { name, level }
 * @returns {Promise<object>} 会员信息
 */
export function updateMember(id, data) {
  return request(`/api/members/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

/**
 * 会员充值
 * @param {number} id 会员 ID
 * @param {object} data { amount, giftAmount, bonusPoints }
 * @returns {Promise<object>} 会员信息
 */
export function rechargeMember(id, data) {
  return request(`/api/members/${id}/recharge`, {
    method: 'POST',
    body: JSON.stringify({
      amount: data.amount,
      gift_amount: data.giftAmount || 0,
      bonus_points: data.bonusPoints || 0,
    }),
  })
}

/**
 * 会员积分调整
 * @param {number} id 会员 ID
 * @param {number} points 积分变动值（正增负减）
 * @returns {Promise<object>} 会员信息
 */
export function adjustPoints(id, points) {
  return request(`/api/members/${id}/points`, { method: 'POST', body: JSON.stringify({ points }) })
}

/**
 * 会员概览统计
 * @returns {Promise<object>} 统计与消费排行
 */
export function fetchMemberStats() {
  return request('/api/members/stats')
}

/**
 * 分页查询会员流水
 * @param {object} params { memberId, type, page, pageSize }
 * @returns {Promise<object>} 流水分页数据
 */
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

/**
 * 查询促销列表
 * @param {object} params { enabled }
 * @returns {Promise<Array<object>>} 促销列表
 */
export function fetchPromotions(params = {}) {
  return request(`/api/promotions${query({ enabled: params.enabled })}`)
}

/**
 * 新建促销
 * @param {object} data 促销数据
 * @returns {Promise<object>} 促销信息
 */
export function createPromotion(data) {
  return request('/api/promotions', { method: 'POST', body: JSON.stringify(data) })
}

/**
 * 更新促销
 * @param {number} id 促销 ID
 * @param {object} data 促销数据
 * @returns {Promise<object>} 促销信息
 */
export function updatePromotion(id, data) {
  return request(`/api/promotions/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

/**
 * 删除促销
 * @param {number} id 促销 ID
 * @returns {Promise<void>}
 */
export function deletePromotion(id) {
  return request(`/api/promotions/${id}`, { method: 'DELETE' })
}

/* ---------------- 库存 ---------------- */

/**
 * 分页查询库存
 * @param {object} params { keyword, categoryId, lowOnly, page, pageSize }
 * @returns {Promise<object>} 库存分页数据
 */
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

/**
 * 库存预警清单
 * @returns {Promise<object>} 预警商品
 */
export function fetchInventoryAlerts() {
  return request('/api/inventory/alerts')
}

/**
 * 采购入库
 * @param {object} data { productId, qty, costPrice }
 * @returns {Promise<object>} 入库结果
 */
export function inventoryInbound(data) {
  return request('/api/inventory/inbound', {
    method: 'POST',
    body: JSON.stringify({ product_id: data.productId, qty: data.qty, cost_price: data.costPrice }),
  })
}

/**
 * 库存盘点
 * @param {object} data { productId, actual }
 * @returns {Promise<object>} 盘点结果
 */
export function inventoryStocktake(data) {
  return request('/api/inventory/stocktake', {
    method: 'POST',
    body: JSON.stringify({ product_id: data.productId, actual: data.actual }),
  })
}

/**
 * 库存报损
 * @param {object} data { productId, qty }
 * @returns {Promise<object>} 报损结果
 */
export function inventoryBreakage(data) {
  return request('/api/inventory/breakage', {
    method: 'POST',
    body: JSON.stringify({ product_id: data.productId, qty: data.qty }),
  })
}

/**
 * 分页查询库存流水
 * @param {object} params { productId, type, page, pageSize }
 * @returns {Promise<object>} 流水分页数据
 */
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

/* ---------------- 商品 / 分类（下拉选项） ---------------- */

/**
 * 分页查询商品
 * @param {object} params { keyword, categoryId, pricingMode, enabled, page, pageSize }
 * @returns {Promise<object>} 商品分页数据
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

/**
 * 新增商品
 * @param {object} data 商品数据（后端字段命名）
 * @returns {Promise<object>} 商品信息
 */
export function createProduct(data) {
  return request('/api/products', { method: 'POST', body: JSON.stringify(data) })
}

/**
 * 更新商品
 * @param {number} id 商品 ID
 * @param {object} data 商品数据（后端字段命名）
 * @returns {Promise<object>} 商品信息
 */
export function updateProduct(id, data) {
  return request(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}

/**
 * 删除商品
 * @param {number} id 商品 ID
 * @returns {Promise<void>}
 */
export function deleteProduct(id) {
  return request(`/api/products/${id}`, { method: 'DELETE' })
}

/**
 * 批量改价
 * @param {object} data { mode, categoryId, productIds, adjustType, value }
 * @returns {Promise<object>} 调整结果
 */
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

/**
 * Excel 导入商品
 * @param {File} file xlsx 文件
 * @returns {Promise<object>} 导入结果
 */
export function importProducts(file) {
  return upload('/api/products/import', file)
}

/**
 * 商品导出地址（浏览器直接下载）
 * @returns {string} 导出接口地址
 */
export function productExportUrl() {
  return `${BASE_URL}/api/products/export`
}

/**
 * 商品导入模板下载地址
 * @returns {string} 模板接口地址
 */
export function productTemplateUrl() {
  return `${BASE_URL}/api/products/import-template`
}

/**
 * 查询分类树
 * @returns {Promise<Array<object>>} 分类树
 */
export function fetchCategoryTree() {
  return request('/api/categories/tree')
}

/**
 * 查询分类树（兼容旧调用名）
 * @returns {Promise<Array<object>>} 分类树
 */
export function fetchCategories() {
  return fetchCategoryTree()
}

/**
 * 新增分类
 * @param {object} data { name, parentId, sort, enabled }
 * @returns {Promise<object>} 分类信息
 */
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

/**
 * 更新分类
 * @param {number} id 分类 ID
 * @param {object} data { name, parentId, sort, enabled }
 * @returns {Promise<object>} 分类信息
 */
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

/**
 * 删除分类
 * @param {number} id 分类 ID
 * @returns {Promise<void>}
 */
export function deleteCategory(id) {
  return request(`/api/categories/${id}`, { method: 'DELETE' })
}

/* ---------------- 订单 ---------------- */

/**
 * 分页查询订单
 * @param {object} params { start, end, status, page, pageSize }
 * @returns {Promise<object>} 订单分页数据
 */
export function fetchOrders(params = {}) {
  return request(
    `/api/orders${query({
      start: params.start,
      end: params.end,
      status: params.status,
      page: params.page,
      page_size: params.pageSize,
    })}`,
  )
}

/* ---------------- 报表 ---------------- */

/**
 * 销售日报月报
 * @param {object} params { start, end, mode }
 * @returns {Promise<object>} 汇总与趋势
 */
export function fetchDailyReport(params = {}) {
  return request(`/api/reports/daily${query({ start: params.start, end: params.end, mode: params.mode })}`)
}

/**
 * 商品销售排行
 * @param {object} params { start, end, limit }
 * @returns {Promise<object>} 排行数据
 */
export function fetchProductRank(params = {}) {
  return request(`/api/reports/products${query({ start: params.start, end: params.end, limit: params.limit })}`)
}

/**
 * 时段分析
 * @param {object} params { start, end }
 * @returns {Promise<object>} 时段数据
 */
export function fetchHourlyReport(params = {}) {
  return request(`/api/reports/hourly${query({ start: params.start, end: params.end })}`)
}

/**
 * 毛利分析
 * @param {object} params { start, end }
 * @returns {Promise<object>} 毛利数据
 */
export function fetchProfitReport(params = {}) {
  return request(`/api/reports/profit${query({ start: params.start, end: params.end })}`)
}

/**
 * 会员分析
 * @param {object} params { start, end, limit }
 * @returns {Promise<object>} 会员分析数据
 */
export function fetchMemberReport(params = {}) {
  return request(`/api/reports/members${query({ start: params.start, end: params.end, limit: params.limit })}`)
}
