// 后台管理 API 封装：统一请求后端 FastAPI 服务

const BASE_URL = 'http://127.0.0.1:8000'
// 后台登录令牌缓存键
const TOKEN_KEY = 'admin_token'
// 当前门店 ID 缓存键
const STORE_KEY = 'admin_store_id'
// 可访问门店列表缓存键
const STORES_KEY = 'admin_stores'
// 当前登录用户信息缓存键
const USER_KEY = 'admin_user'

/**
 * 保存当前登录用户信息（用于菜单权限判断）
 * @param {object} user 用户信息 { id, username, name, role }
 */
export function setUserInfo(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user || {}))
}

/**
 * 读取当前登录用户信息
 * @returns {object} 用户信息（未登录时为空对象）
 */
export function getUserInfo() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || '{}')
  } catch {
    return {}
  }
}

/**
 * 清除当前登录用户信息
 */
export function clearUserInfo() {
  localStorage.removeItem(USER_KEY)
}

/**
 * 当前用户是否为平台超级管理员
 * @returns {boolean} 是超级管理员返回 true
 */
export function isSuperAdmin() {
  return getUserInfo().role === 'super'
}

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
 * 保存可访问门店列表（登录成功后调用）
 * @param {Array<{id:string,name:string}>} stores 门店列表
 */
export function setStores(stores) {
  localStorage.setItem(STORES_KEY, JSON.stringify(stores || []))
}

/**
 * 读取可访问门店列表
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
 * 清除门店相关缓存（退出登录时调用）
 */
export function clearStoreInfo() {
  localStorage.removeItem(STORE_KEY)
  localStorage.removeItem(STORES_KEY)
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
  const storeId = getCurrentStore()
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(storeId ? { 'X-Store-Id': storeId } : {}),
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
  const storeId = getCurrentStore()
  const form = new FormData()
  form.append('file', file)
  const headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  if (storeId) headers['X-Store-Id'] = storeId
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers,
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

/* ---------------- 用户 / 日志 / 设置 / 备份 ---------------- */

/**
 * 分页查询后台用户
 * @param {object} params { keyword, page, pageSize }
 * @returns {Promise<object>} 用户分页数据
 */
export function fetchUsers(params = {}) {
  return request(
    `/api/users${query({ keyword: params.keyword, page: params.page, page_size: params.pageSize })}`,
  )
}

/**
 * 新增后台用户
 * @param {object} data { username, name, role, password }
 * @returns {Promise<object>} 用户信息
 */
export function createUser(data) {
  return request('/api/users', {
    method: 'POST',
    body: JSON.stringify({
      username: data.username,
      name: data.name,
      role: data.role,
      password: data.password || null,
    }),
  })
}

/**
 * 更新后台用户
 * @param {number} id 用户 ID
 * @param {object} data { name, role, enabled, password }
 * @returns {Promise<object>} 用户信息
 */
export function updateUser(id, data) {
  return request(`/api/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

/**
 * 重置用户密码为默认密码
 * @param {number} id 用户 ID
 * @returns {Promise<object>} 用户信息
 */
export function resetUserPassword(id) {
  return request(`/api/users/${id}/reset-password`, { method: 'POST' })
}

/**
 * 分页查询操作日志
 * @param {object} params { keyword, page, pageSize }
 * @returns {Promise<object>} 日志分页数据
 */
export function fetchOperationLogs(params = {}) {
  return request(
    `/api/operation-logs${query({
      keyword: params.keyword,
      page: params.page,
      page_size: params.pageSize,
    })}`,
  )
}

/**
 * 读取系统设置（全部分组）
 * @returns {Promise<object>} { store, cashier }
 */
export function fetchSettings() {
  return request('/api/settings')
}

/**
 * 保存指定分组设置
 * @param {string} group 分组名（store/cashier）
 * @param {object} data 设置内容
 * @returns {Promise<object>} 保存后的设置
 */
export function saveSettings(group, data) {
  return request(`/api/settings/${group}`, { method: 'PUT', body: JSON.stringify(data) })
}

/**
 * 查询备份列表
 * @returns {Promise<Array<object>>} 备份文件列表
 */
export function fetchBackups() {
  return request('/api/backups')
}

/**
 * 立即创建备份
 * @returns {Promise<object>} 新备份文件
 */
export function createBackup() {
  return request('/api/backups', { method: 'POST' })
}

/**
 * 备份下载地址
 * @param {string} name 备份文件名
 * @returns {string} 下载接口地址
 */
export function backupDownloadUrl(name) {
  return `${BASE_URL}/api/backups/${encodeURIComponent(name)}/download`
}

/* ---------------- 租户管理（平台超级管理员） ---------------- */

/**
 * 查询租户列表（超级管理员见全部，租户管理员仅见本租户）
 * @returns {Promise<Array<object>>} 租户列表（含门店数/用户数统计）
 */
export function fetchTenants() {
  return request('/api/tenants')
}

/**
 * 新增租户（可同时开通初始管理员与默认门店）
 * @param {object} data { name, code, enabled, adminUsername, adminPassword, adminName }
 * @returns {Promise<object>} 租户信息
 */
export function createTenant(data) {
  return request('/api/tenants', {
    method: 'POST',
    body: JSON.stringify({
      name: data.name,
      code: data.code,
      enabled: data.enabled ?? true,
      admin_username: data.adminUsername || null,
      admin_password: data.adminPassword || null,
      admin_name: data.adminName || null,
    }),
  })
}

/**
 * 更新租户信息
 * @param {number} id 租户 ID
 * @param {object} data { name, code, enabled }
 * @returns {Promise<object>} 租户信息
 */
export function updateTenant(id, data) {
  return request(`/api/tenants/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
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
