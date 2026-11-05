// 后台管理 API 封装：统一请求后端 FastAPI 服务

const BASE_URL = 'http://127.0.0.1:8000'

/**
 * 发起 JSON 请求并解析响应
 * @param {string} path 接口路径
 * @param {object} options fetch 选项
 * @returns {Promise<any>} 解析后的数据
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
 * 查询商品列表（下拉选项用）
 * @returns {Promise<object>} 商品分页数据
 */
export function fetchProducts() {
  return request('/api/products?page_size=200')
}

/**
 * 查询分类树（下拉选项用）
 * @returns {Promise<Array<object>>} 分类树
 */
export function fetchCategories() {
  return request('/api/categories/tree')
}
