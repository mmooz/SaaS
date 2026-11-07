import Database from '@tauri-apps/plugin-sql'
import { getCurrentStore } from '../../api.js'

// 本地 SQLite 数据库文件（由 Tauri SQL 插件写入应用数据目录）
const DB_PATH = 'sqlite:pos-offline.db'
// 浏览器环境下退化为 localStorage 存储键
const LS_FALLBACK = 'pos_offline_db'

// 表结构：本机订单、待上传队列、本机班次
const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS local_orders (
    order_no TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS offline_queue (
    queue_key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
  )`,
  `CREATE TABLE IF NOT EXISTS local_shifts (
    shift_id TEXT PRIMARY KEY,
    cashier_id TEXT,
    store_id TEXT,
    start_at TEXT NOT NULL,
    end_at TEXT,
    base_cash REAL DEFAULT 0,
    total_sales REAL DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'open',
    synced INTEGER DEFAULT 0
  )`,
  // Q25：死信队列，隔离服务端明确拒绝（4xx/5xx）的队列项，避免阻塞后续补传
  `CREATE TABLE IF NOT EXISTS dead_letter_queue (
    queue_key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    reason TEXT NOT NULL,
    failed_at TEXT NOT NULL
  )`,
  'CREATE INDEX IF NOT EXISTS idx_queue_kind ON offline_queue(kind, created_at)',
  'CREATE INDEX IF NOT EXISTS idx_orders_shift ON local_orders(created_at)',
]

// Q26：兼容旧库的增量列。旧库已存在同名列时 SQLite 会报错，逐条 try/catch 忽略，
// 不引入 Alembic 之外的迁移框架，也不改动既有行数据。
const MIGRATIONS = ['ALTER TABLE local_shifts ADD COLUMN store_id TEXT']

/**
 * 规范化队列主键：兼容调用方传业务 key（订单号）或 listQueue 返回的完整 queue_key。
 * Q25：修掉既有 bug——原先 removeQueueItem('order', item.key) 会把完整键再拼一次
 * 前缀，导致成功上传的队列项删不掉。
 * @param {string} kind 队列类型 order/refund/shift
 * @param {string} key 业务主键或完整队列键
 * @returns {string} 规范化后的队列主键
 */
function normalizeQueueKey(kind, key) {
  const raw = String(key)
  return raw.startsWith(`${kind}:`) ? raw : `${kind}:${raw}`
}

/**
 * 离线数据仓库：桌面端使用 Tauri SQLite，浏览器环境使用 localStorage 兜底。
 *
 * 保存三类数据：
 * 1. 本机订单：无论在线/离线都落库，离线退款查询与班次汇总依赖它；
 * 2. 待上传队列：订单/退货/班次的补传任务，联网后按时间顺序上传；
 * 3. 本机班次：离线开班与交班记录，联网后补传后端。
 */
export class OfflineStore {
  constructor() {
    // SQLite 数据库连接（非 Tauri 环境为 null）
    this.db = null
    // 初始化中的 Promise，避免并发重复打开数据库
    this.loading = null
    // 是否运行在 Tauri 桌面壳内
    this.tauri = typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__
    // 浏览器兜底存储的数据对象
    this.memory = null
  }

  /**
   * 初始化存储（打开 SQLite 并建表；失败时自动降级到 localStorage）
   * @returns {Promise<void>}
   */
  async init() {
    if (!this.tauri) {
      this.loadMemory()
      return
    }
    if (this.db) return
    if (this.loading) return this.loading
    this.loading = (async () => {
      try {
        this.db = await Database.load(DB_PATH)
        for (const sql of SCHEMA) {
          await this.db.execute(sql)
        }
        // 旧库补列：已存在该列时忽略错误，保证初始化不被打断
        for (const sql of MIGRATIONS) {
          try {
            await this.db.execute(sql)
          } catch {
            // 列已存在，无需处理
          }
        }
      } catch (err) {
        // 插件不可用时退化为本地存储，保证收银不中断
        console.warn('离线数据库初始化失败，已降级为 localStorage：', err)
        this.tauri = false
        this.db = null
        this.loadMemory()
      }
    })()
    await this.loading
    this.loading = null
  }

  /**
   * 读取浏览器兜底存储
   */
  loadMemory() {
    if (this.memory) return
    try {
      const raw = localStorage.getItem(LS_FALLBACK)
      this.memory = raw ? JSON.parse(raw) : { orders: {}, queue: {}, shifts: {} }
    } catch {
      this.memory = { orders: {}, queue: {}, shifts: {} }
    }
    // 兼容旧数据缺失字段
    this.memory.orders = this.memory.orders || {}
    this.memory.queue = this.memory.queue || {}
    this.memory.shifts = this.memory.shifts || {}
    // Q25：兼容旧数据缺失死信分支
    this.memory.deadLetters = this.memory.deadLetters || {}
  }

  /**
   * 持久化浏览器兜底存储
   */
  saveMemory() {
    localStorage.setItem(LS_FALLBACK, JSON.stringify(this.memory))
  }

  /**
   * 保存/更新本机订单
   * @param {object} order 订单数据（含本地生成的 id、明细 id）
   * @returns {Promise<void>}
   */
  async saveLocalOrder(order) {
    await this.init()
    const payload = JSON.stringify(order)
    const createdAt = order.created_at || new Date().toISOString()
    if (!this.tauri) {
      this.memory.orders[order.order_no] = { payload, created_at: createdAt }
      this.saveMemory()
      return
    }
    await this.db.execute(
      `INSERT INTO local_orders(order_no, payload, created_at) VALUES (?, ?, ?)
       ON CONFLICT(order_no) DO UPDATE SET payload = excluded.payload`,
      [order.order_no, payload, createdAt],
    )
  }

  /**
   * 按订单号删除本机订单（R12：在线结算被服务端业务校验拒绝时回滚本地落库）
   *
   * Tauri 分支执行 DELETE，浏览器兜底分支删除内存记录并持久化，两分支行为一致。
   * 订单号不存在时静默成功，便于调用方无条件回滚。
   * @param {string} orderNo 订单号
   * @returns {Promise<void>}
   */
  async removeLocalOrder(orderNo) {
    await this.init()
    if (!this.tauri) {
      delete this.memory.orders[orderNo]
      this.saveMemory()
      return
    }
    await this.db.execute('DELETE FROM local_orders WHERE order_no = ?', [orderNo])
  }

  /**
   * 按订单号读取本机订单
   * @param {string} orderNo 订单号
   * @returns {Promise<object|null>} 订单数据
   */
  async getLocalOrder(orderNo) {
    await this.init()
    if (!this.tauri) {
      const row = this.memory.orders[orderNo]
      return row ? JSON.parse(row.payload) : null
    }
    const rows = await this.db.select('SELECT payload FROM local_orders WHERE order_no = ?', [
      orderNo,
    ])
    return rows.length ? JSON.parse(rows[0].payload) : null
  }

  /**
   * 按关键字检索本机订单（订单号或会员手机号）
   * @param {string} keyword 关键字
   * @param {number} limit 最大返回数量
   * @returns {Promise<object[]>} 订单列表（按下单时间倒序）
   */
  async searchLocalOrders(keyword, limit = 20) {
    await this.init()
    const kw = (keyword || '').trim()
    if (!this.tauri) {
      return Object.values(this.memory.orders)
        .map((row) => JSON.parse(row.payload))
        .filter((order) => this.matchOrder(order, kw))
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
        .slice(0, limit)
    }
    // Q25：先按关键字过滤再 LIMIT，与浏览器兜底分支行为一致，
    // 避免「先取最近 20 条再过滤」导致更早的匹配订单搜不到。
    const like = `%${kw}%`
    const rows = await this.db.select(
      'SELECT payload FROM local_orders WHERE order_no LIKE ? OR payload LIKE ? ORDER BY created_at DESC LIMIT ?',
      [like, like, limit],
    )
    return rows.map((row) => JSON.parse(row.payload))
  }

  /**
   * 判断订单是否匹配关键字
   * @param {object} order 订单数据
   * @param {string} keyword 关键字
   * @returns {boolean} 是否匹配
   */
  matchOrder(order, keyword) {
    if (!keyword) return true
    return (
      (order.order_no || '').includes(keyword) ||
      (order.member_mobile || '').includes(keyword)
    )
  }

  /**
   * 查询本机某班次的订单（班次汇总用）
   * @param {string|null} shiftId 班次 ID
   * @returns {Promise<object[]>} 订单列表
   */
  async listOrdersByShift(shiftId) {
    await this.init()
    if (!shiftId) return []
    if (!this.tauri) {
      return Object.values(this.memory.orders)
        .map((row) => JSON.parse(row.payload))
        .filter((order) => order.shift_id === shiftId)
    }
    const rows = await this.db.select('SELECT payload FROM local_orders ORDER BY created_at ASC')
    return rows
      .map((row) => JSON.parse(row.payload))
      .filter((order) => order.shift_id === shiftId)
  }

  /**
   * 写入待上传队列（同 key 幂等覆盖）
   * @param {string} kind 类型：order/refund/shift
   * @param {string} key 业务主键（订单号/退款单号/班次 ID）
   * @param {object} payload 上传载荷
   * @param {string} [createdAt] 发生时间
   * @returns {Promise<void>}
   */
  async queueItem(kind, key, payload, createdAt) {
    await this.init()
    const data = JSON.stringify(payload)
    const time = createdAt || new Date().toISOString()
    const queueKey = normalizeQueueKey(kind, key)
    if (!this.tauri) {
      this.memory.queue[queueKey] = { kind, payload: data, created_at: time }
      this.saveMemory()
      return
    }
    await this.db.execute(
      `INSERT INTO offline_queue(queue_key, kind, payload, created_at) VALUES (?, ?, ?, ?)
       ON CONFLICT(queue_key) DO UPDATE SET payload = excluded.payload`,
      [queueKey, kind, data, time],
    )
  }

  /**
   * 列出待上传队列
   * @param {string|null} kind 类型过滤（空表示全部）
   * @returns {Promise<Array<{key:string, kind:string, payload:object, created_at:string}>>} 队列项
   */
  async listQueue(kind = null) {
    await this.init()
    let rows
    if (!this.tauri) {
      rows = Object.entries(this.memory.queue).map(([key, value]) => ({
        queue_key: key,
        kind: value.kind,
        payload: value.payload,
        created_at: value.created_at,
      }))
    } else if (kind) {
      rows = await this.db.select(
        'SELECT queue_key, kind, payload, created_at FROM offline_queue WHERE kind = ? ORDER BY created_at ASC',
        [kind],
      )
    } else {
      rows = await this.db.select(
        'SELECT queue_key, kind, payload, created_at FROM offline_queue ORDER BY created_at ASC',
      )
    }
    return rows
      .filter((row) => !kind || row.kind === kind)
      .sort((a, b) => (a.created_at < b.created_at ? -1 : 1))
      .map((row) => ({
        key: row.queue_key,
        kind: row.kind,
        payload: JSON.parse(row.payload),
        created_at: row.created_at,
      }))
  }

  /**
   * 移除已上传的队列项
   * @param {string} kind 类型
   * @param {string} key 业务主键
   * @returns {Promise<void>}
   */
  async removeQueueItem(kind, key) {
    await this.init()
    const queueKey = normalizeQueueKey(kind, key)
    if (!this.tauri) {
      delete this.memory.queue[queueKey]
      this.saveMemory()
      return
    }
    await this.db.execute('DELETE FROM offline_queue WHERE queue_key = ?', [queueKey])
  }

  /**
   * 统计待上传队列数量
   * @returns {Promise<number>} 队列项数量
   */
  async queueCount() {
    await this.init()
    if (!this.tauri) return Object.keys(this.memory.queue).length
    const rows = await this.db.select('SELECT COUNT(*) AS total FROM offline_queue')
    return Number(rows[0]?.total || 0)
  }

  /**
   * 把被服务端明确拒绝的队列项移到死信队列（Q25）
   * 同时从主队列移除，保证坏数据不再阻塞后续项；同一队列项重复失败时覆盖原因。
   * @param {string} kind 类型 order/refund/shift
   * @param {string} key 业务主键或完整队列键
   * @param {object|string} payload 原始载荷
   * @param {string} reason 失败原因（含 HTTP 状态与错误文案）
   * @param {string} [failedAt] 失败时间
   * @returns {Promise<void>}
   */
  async moveToDeadLetter(kind, key, payload, reason, failedAt) {
    await this.init()
    const queueKey = normalizeQueueKey(kind, key)
    const data = typeof payload === 'string' ? payload : JSON.stringify(payload || {})
    const time = failedAt || new Date().toISOString()
    if (!this.tauri) {
      delete this.memory.queue[queueKey]
      this.memory.deadLetters[queueKey] = {
        kind, payload: data, reason, failed_at: time,
      }
      this.saveMemory()
      return
    }
    await this.db.execute('DELETE FROM offline_queue WHERE queue_key = ?', [queueKey])
    await this.db.execute(
      `INSERT INTO dead_letter_queue(queue_key, kind, payload, reason, failed_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(queue_key) DO UPDATE SET
         payload = excluded.payload,
         reason = excluded.reason,
         failed_at = excluded.failed_at`,
      [queueKey, kind, data, reason, time],
    )
  }

  /**
   * 列出死信队列（供监控与人工重放查询）
   * @returns {Promise<Array<{key:string,kind:string,payload:object,reason:string,failed_at:string}>>}
   */
  async listDeadLetters() {
    await this.init()
    let rows
    if (!this.tauri) {
      rows = Object.entries(this.memory.deadLetters).map(([key, value]) => ({
        queue_key: key,
        kind: value.kind,
        payload: value.payload,
        reason: value.reason,
        failed_at: value.failed_at,
      }))
    } else {
      rows = await this.db.select(
        'SELECT queue_key, kind, payload, reason, failed_at FROM dead_letter_queue ORDER BY failed_at DESC',
      )
    }
    return rows
      .sort((a, b) => (a.failed_at < b.failed_at ? 1 : -1))
      .map((row) => ({
        key: row.queue_key,
        kind: row.kind,
        payload: JSON.parse(row.payload),
        reason: row.reason,
        failed_at: row.failed_at,
      }))
  }

  /**
   * 统计死信队列数量（供监控查询）
   * @returns {Promise<number>} 死信项数量
   */
  async deadLetterCount() {
    await this.init()
    if (!this.tauri) return Object.keys(this.memory.deadLetters).length
    const rows = await this.db.select('SELECT COUNT(*) AS total FROM dead_letter_queue')
    return Number(rows[0]?.total || 0)
  }

  /**
   * 保存/更新本机班次
   * @param {object} shift 班次数据
   * @returns {Promise<void>}
   */
  async saveLocalShift(shift) {
    await this.init()
    // Q26：固化快照写入（开班/交班发生）时的门店。调用方未显式传入时，
    // 由离线仓库统一从当前门店兜底，避免改动 4 个视图调用点造成遗漏。
    const rawStoreId =
      shift.store_id !== undefined && shift.store_id !== null && String(shift.store_id) !== ''
        ? String(shift.store_id)
        : getCurrentStore() || null
    const row = {
      shift_id: shift.id,
      cashier_id: shift.cashier_id || null,
      store_id: rawStoreId,
      start_at: shift.start_at,
      end_at: shift.end_at || null,
      base_cash: Number(shift.base_cash) || 0,
      total_sales: Number(shift.total_sales) || 0,
      order_count: Number(shift.order_count) || 0,
      status: shift.status || 'open',
      synced: shift.synced ? 1 : 0,
    }
    if (!this.tauri) {
      // 浏览器兜底为对象存储，直接写入新字段，无需迁移
      this.memory.shifts[row.shift_id] = row
      this.saveMemory()
      return
    }
    await this.db.execute(
      `INSERT INTO local_shifts(shift_id, cashier_id, store_id, start_at, end_at, base_cash, total_sales, order_count, status, synced)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(shift_id) DO UPDATE SET
         store_id = COALESCE(local_shifts.store_id, excluded.store_id),
         end_at = excluded.end_at,
         base_cash = excluded.base_cash,
         total_sales = excluded.total_sales,
         order_count = excluded.order_count,
         status = excluded.status,
         synced = excluded.synced`,
      [
        row.shift_id,
        row.cashier_id,
        row.store_id,
        row.start_at,
        row.end_at,
        row.base_cash,
        row.total_sales,
        row.order_count,
        row.status,
        row.synced,
      ],
    )
  }

  /**
   * 按班次 ID 读取本机班次
   * @param {string} shiftId 班次 ID
   * @returns {Promise<object|null>} 班次数据
   */
  async getLocalShift(shiftId) {
    await this.init()
    if (!this.tauri) {
      return this.memory.shifts[shiftId] || null
    }
    const rows = await this.db.select('SELECT * FROM local_shifts WHERE shift_id = ?', [shiftId])
    return rows.length ? rows[0] : null
  }

  /**
   * 查询收银员本机进行中的班次
   * @param {string} cashierId 收银员用户 ID
   * @returns {Promise<object|null>} 进行中的班次
   */
  async getOpenShift(cashierId) {
    await this.init()
    if (!this.tauri) {
      return (
        Object.values(this.memory.shifts).find(
          (shift) => shift.status === 'open' && String(shift.cashier_id) === String(cashierId),
        ) || null
      )
    }
    const rows = await this.db.select(
      "SELECT * FROM local_shifts WHERE status = 'open' AND cashier_id = ? ORDER BY start_at DESC LIMIT 1",
      [String(cashierId)],
    )
    return rows.length ? rows[0] : null
  }

  /**
   * 列出尚未补传成功的本机班次
   * @returns {Promise<object[]>} 待补传班次
   */
  async listPendingShifts() {
    await this.init()
    if (!this.tauri) {
      return Object.values(this.memory.shifts).filter((shift) => !shift.synced)
    }
    return this.db.select('SELECT * FROM local_shifts WHERE synced = 0 ORDER BY start_at ASC')
  }

  /**
   * 标记班次已补传
   * @param {string} shiftId 班次 ID
   * @returns {Promise<void>}
   */
  async markShiftSynced(shiftId) {
    await this.init()
    if (!this.tauri) {
      if (this.memory.shifts[shiftId]) {
        this.memory.shifts[shiftId].synced = 1
        this.saveMemory()
      }
      return
    }
    await this.db.execute('UPDATE local_shifts SET synced = 1 WHERE shift_id = ?', [shiftId])
  }
}

// 应用内共享的离线仓库实例
export const offlineStore = new OfflineStore()
