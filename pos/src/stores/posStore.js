// POS 收银状态管理（Pinia）：商品缓存、购物车、订单上传与离线队列

import { defineStore } from 'pinia'
import { PromotionEngine } from '../services/PromotionEngine.js'
import {
  clearAuthToken,
  clearStoreInfo,
  consumeMember,
  fetchActivePromotions,
  fetchSyncData,
  getCurrentStore,
  getStores,
  isNetworkError,
  refundOrder as apiRefundOrder,
  setAuthToken,
  setCurrentStore,
  setStores,
  syncShifts,
  uploadOrder,
} from '../api.js'
import { offlineStore } from '../services/offline/OfflineStore.js'
import { offlineSnowflake } from '../services/offline/Snowflake.js'
import { getDeviceId } from '../services/offline/deviceId.js'

// localStorage 键名
const LS_PRODUCTS = 'pos_products' // 商品本地缓存（离线可用）
const LS_CATEGORIES = 'pos_categories' // 分类本地缓存
const LS_PROMOTIONS = 'pos_promotions' // 生效促销本地缓存
const LS_MEMBERS = 'pos_members' // 会员档案本地缓存（仅身份识别 + 会员价，不含余额）
const LS_LAST_SYNC = 'pos_last_sync_time' // 增量同步游标（重启后不丢）
const LS_CART = 'pos_cart' // 购物车本地缓存
const LS_HANG = 'pos_hang_orders' // 挂单本地缓存
const LS_OFFLINE = 'pos_offline_orders' // 待上传订单队列
const LS_CASHIER = 'pos_cashier' // 已登录收银员（重启后保持登录）
const LS_SHIFT = 'pos_shift_id' // 当前进行中的班次 ID（订单归属用）

/**
 * 从 localStorage 读取 JSON，解析失败返回默认值
 * @param {string} key 键名
 * @param {*} fallback 默认值
 */
function loadLS(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

export const usePosStore = defineStore('pos', {
  state: () => ({
    // 商品与分类（来自后端同步）
    products: loadLS(LS_PRODUCTS, []),
    categories: loadLS(LS_CATEGORIES, []),
    // 同步状态：idle/syncing/synced/error
    syncState: 'idle',
    syncError: '',
    // Q07：增量游标持久化，POS 重启后不丢
    lastSyncTime: loadLS(LS_LAST_SYNC, null),
    // 当前收银员（从本地缓存恢复，退出登录后清空）
    cashier: loadLS(LS_CASHIER, null),
    // 当前选中的门店（从本地缓存恢复，用于请求头 X-Store-Id）
    currentStore: (() => {
      const storeId = getCurrentStore()
      const stores = getStores()
      return stores.find((s) => String(s.id) === storeId) || null
    })(),
    // 当前进行中的班次 ID（订单上传时归属班次，未接班为 null）
    shiftId: loadLS(LS_SHIFT, null),
    // 当前识别的会员（null 表示散客）
    member: null,
    // Q19：会员档案本地缓存（增量 upsert，仅档案字段，绝不含余额/资金路径）
    members: loadLS(LS_MEMBERS, []),
    // 当前生效的促销规则
    promotions: loadLS(LS_PROMOTIONS, []),
    // 购物车
    cart: loadLS(LS_CART, []),
    // 挂单列表
    hangOrders: loadLS(LS_HANG, []),
    // 待上传订单队列（启动后从本地离线数据库加载）
    offlineOrders: [],
    // Q25：死信队列镜像（被服务端明确拒绝的队列项，供监控/人工重放）
    deadLetters: [],
  }),

  getters: {
    // 是否已识别会员（决定会员价是否生效）
    memberActive(state) {
      return !!state.member
    },
    // 购物车单品成交单价：零售价、会员价与促销价取最低
    itemPrice(state) {
      return (item) => PromotionEngine.itemPrice(item, state.promotions, state.member)
    },
    // 购物车单品成交金额：按件=单价×数量，称重=单价×重量
    itemAmount(state) {
      return (item) => {
        const price = PromotionEngine.itemPrice(item, state.promotions, state.member)
        const raw = item.weighted ? price * item.weight : price * item.qty
        return +raw.toFixed(2)
      }
    },
    // 购物车单品优惠后小计（会员价/特价已生效，未含满减）
    subtotalAmount(state) {
      return state.cart.reduce((sum, i) => {
        const price = PromotionEngine.itemPrice(i, state.promotions, state.member)
        const raw = i.weighted ? price * i.weight : price * i.qty
        return sum + +raw.toFixed(2)
      }, 0)
    },
    // 整单满减优惠金额
    orderDiscount(state) {
      return PromotionEngine.orderDiscount(this.subtotalAmount, state.promotions)
    },
    // 应收合计（单品优惠 + 满减后）
    totalAmount() {
      return +Math.max(0, this.subtotalAmount - this.orderDiscount).toFixed(2)
    },
    // 购物车按零售价计算的合计（用于展示优惠金额）
    retailAmount(state) {
      return state.cart.reduce((sum, i) => {
        const raw = i.weighted ? i.price * i.weight : i.price * i.qty
        return sum + +raw.toFixed(2)
      }, 0)
    },
    // 单品层面优惠金额（会员价/特价合计）
    itemDiscount() {
      return Math.max(0, +(this.retailAmount - this.subtotalAmount).toFixed(2))
    },
    // 购物车商品数
    cartCount(state) {
      return state.cart.length
    },
    // 是否有待上传的离线订单
    hasOfflineOrders(state) {
      return state.offlineOrders.length > 0
    },
    // Q25：死信队列数量（供监控/查询，不强制改 UI）
    deadLetterCount(state) {
      return state.deadLetters.length
    },
  },

  actions: {
    /**
     * 初始化离线数据库并恢复待上传队列（应用启动时调用）
     * @returns {Promise<void>}
     */
    async initOffline() {
      await offlineStore.init()
      await this.reloadOfflineOrders()
      await this.reloadDeadLetters()
      // 旧版本 localStorage 队列已迁移，清理避免重复
      localStorage.removeItem(LS_OFFLINE)
    },

    /**
     * 从离线仓库刷新死信队列镜像（Q25）
     * @returns {Promise<void>}
     */
    async reloadDeadLetters() {
      this.deadLetters = await offlineStore.listDeadLetters()
    },

    /**
     * 从离线数据库刷新待上传订单镜像
     * @returns {Promise<void>}
     */
    async reloadOfflineOrders() {
      const rows = await offlineStore.listQueue('order')
      this.offlineOrders = rows.map((row) => row.payload)
    },

    /**
     * 同步拉取商品/分类/促销/会员并按 id 增量合并（Q07 / Q19）
     * 绝不再用增量结果整体覆盖本地商品缓存；删除与停用商品按 tombstone 移除。
     */
    async syncProducts() {
      this.syncState = 'syncing'
      try {
        const data = await fetchSyncData(this.lastSyncTime)

        // 1. 商品增量按 id upsert 合并，二次同步不清空本地已有商品
        const changed = Array.isArray(data.products) ? data.products : []
        if (changed.length) {
          const merged = new Map(this.products.map((p) => [String(p.id), p]))
          for (const product of changed) merged.set(String(product.id), product)
          this.products = [...merged.values()]
        }
        // 2. 软删 / 停用 tombstone：从本地缓存移除，离线不再可售
        const removed = new Set(
          [...(data.deleted_ids || []), ...(data.disabled_ids || [])].map(String),
        )
        if (removed.size) {
          this.products = this.products.filter((p) => !removed.has(String(p.id)))
        }
        localStorage.setItem(LS_PRODUCTS, JSON.stringify(this.products))

        // 3. 分类全量替换，且只保留启用分类（服务端已过滤，前端再兜一层）
        this.categories = (data.categories || []).filter((c) => c.enabled !== false)
        localStorage.setItem(LS_CATEGORIES, JSON.stringify(this.categories))

        // 4. 促销以载荷中的门店级全量生效规则为准；旧版服务端无该字段时
        //    才退回 fetchActivePromotions() 在线单独拉取，不再是唯一来源
        if (Array.isArray(data.promotions)) {
          this.promotions = data.promotions
          localStorage.setItem(LS_PROMOTIONS, JSON.stringify(this.promotions))
        } else {
          try {
            const promos = await fetchActivePromotions()
            this.promotions = promos
            localStorage.setItem(LS_PROMOTIONS, JSON.stringify(promos))
          } catch {
            // 在线拉取失败时保留本地缓存，下次同步再更新
          }
        }

        // 5. 会员增量按 id upsert；载荷仅含档案字段，不含余额/积分/口令。
        //    本组只用本地会员做身份识别 + 会员价，绝不触碰资金路径。
        const members = Array.isArray(data.members) ? data.members : []
        if (members.length) {
          const mergedMembers = new Map(this.members.map((m) => [String(m.id), m]))
          for (const member of members) mergedMembers.set(String(member.id), member)
          this.members = [...mergedMembers.values()]
          localStorage.setItem(LS_MEMBERS, JSON.stringify(this.members))
        }

        // 6. 游标持久化：server_time 为 naive UTC，重启后仍从该点增量拉取
        if (data.server_time) {
          this.lastSyncTime = data.server_time
          localStorage.setItem(LS_LAST_SYNC, JSON.stringify(this.lastSyncTime))
        }
        this.syncState = 'synced'
        this.syncError = ''
      } catch (err) {
        this.syncState = 'error'
        this.syncError = err.message
      }
    },

    /**
     * 保存登录结果：写入令牌、收银员身份与门店信息（应用重启后保持登录）
     * @param {string} token 登录令牌
     * @param {object} user 收银员信息
     * @param {Array<object>} stores 用户可访问的门店列表
     */
    setAuth(token, user, stores) {
      setAuthToken(token)
      this.setCashier(user)
      // 保存门店列表并默认选中第一个门店
      const storeList = stores || []
      setStores(storeList)
      if (storeList.length > 0) {
        setCurrentStore(storeList[0].id)
        this.currentStore = storeList[0]
      }
    },

    /**
     * 切换当前门店（多门店收银员使用）
     * @param {string} storeId 门店 ID
     */
    switchStore(storeId) {
      const stores = getStores()
      const store = stores.find((s) => String(s.id) === String(storeId))
      if (store) {
        setCurrentStore(store.id)
        this.currentStore = store
      }
    },

    /**
     * 设置当前收银员（同时写入本地缓存，应用重启后保持登录）
     * @param {object} user 收银员信息
     */
    setCashier(user) {
      this.cashier = user
      localStorage.setItem(LS_CASHIER, JSON.stringify(user))
    },

    /**
     * 退出登录：清空令牌、收银员、门店、会员与购物车，避免下一位收银员沿用上一班数据
     */
    clearCashier() {
      this.cashier = null
      this.member = null
      this.shiftId = null
      this.currentStore = null
      this.clearCart()
      localStorage.removeItem(LS_CASHIER)
      localStorage.removeItem(LS_SHIFT)
      clearAuthToken()
      clearStoreInfo()
    },

    /**
     * 设置当前班次（接班后写入，交班后清空）
     * @param {number|null} shiftId 班次 ID
     */
    setShiftId(shiftId) {
      this.shiftId = shiftId || null
      if (shiftId) {
        localStorage.setItem(LS_SHIFT, JSON.stringify(shiftId))
      } else {
        localStorage.removeItem(LS_SHIFT)
      }
    },

    /**
     * 设置当前识别会员（会员价与储值支付随之生效）
     * @param {object|null} member 会员信息
     */
    setMember(member) {
      this.member = member
    },

    /**
     * 清除当前会员（切换为散客）
     */
    clearMember() {
      this.member = null
    },

    /**
     * 按手机号查找本地缓存会员（Q19：离线身份识别 + 会员价专用）
     * 本地缓存由同步载荷增量 upsert，仅含档案字段，不含余额/积分/口令，
     * 绝不用于离线余额扣减、离线储值支付或任何写 balance 的逻辑。
     * @param {string} mobile 手机号
     * @returns {object|null} 会员档案，未命中返回 null
     */
    findLocalMember(mobile) {
      const keyword = String(mobile || '').trim()
      if (!keyword) return null
      return this.members.find((m) => String(m.mobile || '') === keyword) || null
    },

    /**
     * 根据分类 ID 获取分类名称（用于商品列表展示）
     * @param {number|null} categoryId 分类 ID
     * @returns {string} 分类名称
     */
    categoryName(categoryId) {
      const c = this.categories.find((x) => x.id === categoryId)
      return c ? c.name : ''
    },

    /**
     * 添加按件商品到购物车
     * @param {object} product 商品对象
     */
    addCountProduct(product) {
      const item = this.cart.find((i) => i.productId === product.id && !i.weighted)
      if (item) {
        item.qty += 1
        item.amount = +(item.qty * item.price).toFixed(2)
      } else {
        this.cart.push({
          productId: product.id,
          name: product.name,
          price: product.price,
          memberPrice: product.memberPrice || null,
          categoryId: product.categoryId ?? null,
          qty: 1,
          weighted: false,
          amount: product.price,
          weightKey: 'count',
        })
      }
      this.persistCart()
    },

    /**
     * 称重稳定确认：按重量计价入购物车
     * @param {object} product 称重商品
     * @param {number} weight 稳定重量(kg)
     */
    confirmWeighted(product, weight) {
      const amount = +(weight * product.price).toFixed(2)
      this.cart.push({
        productId: product.id,
        name: product.name,
        price: product.price,
        memberPrice: product.memberPrice || null,
        categoryId: product.categoryId ?? null,
        qty: 1,
        weighted: true,
        weight: +weight.toFixed(2),
        amount,
        weightKey: Date.now(),
      })
      this.persistCart()
    },

    /**
     * 购物车数量增减/删除/清空
     */
    incItem(item) {
      item.qty += 1
      item.amount = +(item.qty * item.price).toFixed(2)
      this.persistCart()
    },
    decItem(item) {
      if (item.qty <= 1) return this.removeItem(item)
      item.qty -= 1
      item.amount = +(item.qty * item.price).toFixed(2)
      this.persistCart()
    },
    removeItem(item) {
      this.cart = this.cart.filter((i) => i !== item)
      this.persistCart()
    },
    clearCart() {
      this.cart = []
      this.persistCart()
    },

    /**
     * 挂单/取单/删单
     */
    hangOrder() {
      if (!this.cart.length) return
      this.hangOrders.unshift({
        count: this.cart.length,
        amount: this.totalAmount,
        time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        snapshot: JSON.parse(JSON.stringify(this.cart)),
      })
      localStorage.setItem(LS_HANG, JSON.stringify(this.hangOrders))
      this.clearCart()
    },
    resumeHang(index) {
      this.cart = this.hangOrders[index].snapshot
      this.hangOrders.splice(index, 1)
      localStorage.setItem(LS_HANG, JSON.stringify(this.hangOrders))
      this.persistCart()
    },
    removeHang(index) {
      this.hangOrders.splice(index, 1)
      localStorage.setItem(LS_HANG, JSON.stringify(this.hangOrders))
    },

    /**
     * 结算：生成订单（含雪花 ID）并先落本机，再上传服务端
     * 已识别会员时按会员价计价，储值支付成功后再扣减会员余额
     * @param {object} payload { payMethod, cashReceived, remark }
     * @returns {Promise<{ok:boolean, offline:boolean, orderNo:string, order:object, memberDeducted:boolean}>} 上传结果与本次订单数据
     */
    async settle(payload) {
      const orderNo = this.buildOrderNo()
      // 请求中快照会员，避免结算过程中会员状态被清除
      const member = this.member
      // 订单与明细统一使用离线生成的雪花 ID，补传后保持同一主键
      const now = new Date().toISOString()
      // 逐项按零售价/会员价/促销价取最低计价
      const items = this.cart.map((i) => {
        const unitPrice = PromotionEngine.itemPrice(i, this.promotions, member)
        const amount = +((i.weighted ? unitPrice * i.weight : unitPrice * i.qty)).toFixed(2)
        return {
          id: offlineSnowflake.nextId(),
          created_at: now,
          product_id: i.productId,
          name: i.name,
          qty: i.qty,
          weight_kg: i.weighted ? i.weight : null,
          unit_price: unitPrice,
          amount,
          is_weighted: i.weighted,
          label_printed: i.weighted,
        }
      })
      const subtotal = +items.reduce((sum, i) => sum + i.amount, 0).toFixed(2)
      // 整单满减优惠
      const orderDiscount = PromotionEngine.orderDiscount(subtotal, this.promotions)
      const total = +Math.max(0, subtotal - orderDiscount).toFixed(2)
      // 优惠金额 = 零售价合计 − 实收合计（含会员价/特价/满减）
      const discount = +(this.retailAmount - total).toFixed(2)
      const payDetails = JSON.stringify({ [payload.payMethod]: total })
      // Q26：固化「结算发生时」的门店与可取得的租户，写入订单本体。
      // saveLocalOrder 与离线队列项都基于这个 order 展开，切到别的门店补传时
      // 仍按 store_id 指定单次请求的 X-Store-Id，订单不会被记到当前登录门店。
      const order = {
        id: offlineSnowflake.nextId(),
        order_no: orderNo,
        created_at: now,
        store_id: getCurrentStore() || null,
        tenant_id: this.cashier && this.cashier.tenant_id ? this.cashier.tenant_id : null,
        cashier_id: this.cashier ? this.cashier.id : null,
        shift_id: this.shiftId,
        status: 'paid',
        total_amount: total,
        discount_amount: discount > 0 ? discount : 0,
        pay_details: payDetails,
        member_id: member ? member.id : null,
        member_mobile: member ? member.mobile : null,
        refunded_amount: 0,
        items,
      }
      // 先本地落库：即使断网也不丢单，且离线退款/交班可查询
      await offlineStore.saveLocalOrder(order)
      try {
        await uploadOrder(order)
        this.clearCart()
        await offlineStore.saveLocalOrder({ ...order, synced: true })
        // 储值支付：在线扣减会员余额并按金额累计积分
        let memberDeducted = false
        if (member && payload.payMethod === '储值') {
          try {
            this.member = await consumeMember(member.id, { amount: total, orderNo })
            memberDeducted = true
          } catch {
            memberDeducted = false // 扣款失败不阻塞结算，由后台对账处理
          }
        }
        return { ok: true, offline: false, orderNo, order, memberDeducted }
      } catch (err) {
        // R12：按错误类型分流。服务端 422/409/401 等业务错误说明订单根本不成立，
        // 绝不能当成网络失败塞进离线队列（补传必然再次失败并进死信，业务数据永久丢失，
        // 收银员还会被「离线收款成功」误导）。此类错误必须原样抛回调用方。
        if (!isNetworkError(err)) {
          // 回滚先前的本机落库，避免离线退款/交班列表残留一条无效单；
          // 回滚失败不遮蔽原始业务错误，仅记录到控制台。
          try {
            await offlineStore.removeLocalOrder(orderNo)
          } catch (rollbackErr) {
            console.error('[settle] 回滚本机订单失败', rollbackErr)
          }
          throw err
        }
        // 上传失败（网络不可用）：写入离线队列，联网后自动补传
        await offlineStore.queueItem('order', orderNo, { ...order, offline: true }, now)
        await offlineStore.saveLocalOrder({ ...order, offline: true })
        this.offlineOrders.push({ ...order, offline: true })
        this.clearCart()
        return { ok: false, offline: true, orderNo, order, memberDeducted: false }
      }
    },

    /**
     * 补传离线数据：依次上传班次 → 订单 → 退款（保证退款引用的订单已存在）
     * Q25：按 isNetworkError 分流——网络错误才 break 保留队列；业务错误（4xx/5xx）
     * 记录失败原因并把该项移到死信队列，从主队列移除后继续处理后续项，不再吞整批。
     * R13：班次按门店分组判定，成功分组不被失败分组牵连；网络错误不再提前 return，
     * 订单与退款补传始终继续执行。
     * @returns {Promise<{uploaded:number, deadLettered:number}>} 成功补传数与本次隔离到死信的项数
     */
    async flushOfflineOrders() {
      await this.initOffline()
      let deadLettered = 0
      // 1. 先补传班次，保证离线订单的班次归属有效
      const pendingShifts = await offlineStore.listPendingShifts()
      if (pendingShifts.length) {
        const shiftPayloads = pendingShifts.map((shift) => ({
          id: shift.shift_id,
          cashier_id: shift.cashier_id,
          // Q26：用班次快照固化的发生门店；旧库无该字段时回退当前门店
          store_id: shift.store_id || getCurrentStore() || null,
          start_at: shift.start_at,
          end_at: shift.end_at,
          base_cash: Number(shift.base_cash) || 0,
          total_sales: Number(shift.total_sales) || 0,
          order_count: Number(shift.order_count) || 0,
          status: shift.status,
        }))
        // R13：syncShifts 返回分组级结果，逐组判定成败。
        // 一个门店分组 403 不再让已成功上传的分组一起进死信；网络错误也不再 return，
        // 后续订单/退款补传照常尝试（Q25「不阻断」）。
        const { groups } = await syncShifts(shiftPayloads)
        for (const group of groups || []) {
          const groupShifts = group.items || []
          if (group.ok) {
            // 成功分组：只标记本组班次已同步，绝不进死信
            for (const shift of groupShifts) {
              await offlineStore.markShiftSynced(shift.id)
            }
            continue
          }
          const err = group.error
          if (isNetworkError(err)) {
            // 该组网络不可用：保持未同步（listPendingShifts 仍能查到），不进死信、不中断
            continue
          }
          // 业务错误：只把该分组的班次隔离到死信，reason 带 status 与错误文案
          const reason = `班次补传被服务端拒绝：${err?.status ?? ''} ${err?.message || '未知错误'}`
          for (const shift of groupShifts) {
            await offlineStore.moveToDeadLetter('shift', shift.id, shift, reason)
            await offlineStore.markShiftSynced(shift.id)
            deadLettered += 1
          }
        }
      }
      // 2. 按发生顺序补传订单
      let uploaded = 0
      const pendingOrders = await offlineStore.listQueue('order')
      for (const item of pendingOrders) {
        try {
          await uploadOrder(item.payload)
          await offlineStore.removeQueueItem('order', item.key)
          await offlineStore.saveLocalOrder({ ...item.payload, offline: false, synced: true })
          uploaded += 1
        } catch (err) {
          if (isNetworkError(err)) break // 网络仍不可用，保留队列待下次重试
          await offlineStore.moveToDeadLetter(
            'order', item.key, item.payload,
            `订单补传被服务端拒绝：${err.status ?? ''} ${err.message || '未知错误'}`,
          )
          deadLettered += 1
          // 不 break：坏项已从主队列移除，继续处理后续项
        }
      }
      // 3. 最后补传退款
      const pendingRefunds = await offlineStore.listQueue('refund')
      for (const item of pendingRefunds) {
        try {
          await apiRefundOrder(item.payload.order_no, {
            refundNo: item.payload.refund_no,
            createdAt: item.payload.created_at,
            refundType: item.payload.refund_type,
            itemIds: item.payload.item_ids,
            reason: item.payload.reason,
            cashierId: item.payload.cashier_id,
            authorizerId: item.payload.authorizer_id,
          })
          await offlineStore.removeQueueItem('refund', item.key)
        } catch (err) {
          if (isNetworkError(err)) break
          await offlineStore.moveToDeadLetter(
            'refund', item.key, item.payload,
            `退款补传被服务端拒绝：${err.status ?? ''} ${err.message || '未知错误'}`,
          )
          deadLettered += 1
        }
      }
      await this.reloadOfflineOrders()
      await this.reloadDeadLetters()
      return { uploaded, deadLettered }
    },

    /**
     * 生成本地订单号：<8位设备ID>-<yyyyMMddHHmmss>-<5位序号>
     * Q26：叠加持久化设备标识，两台设备同秒同序号不再产生相同单号；
     * 总长 8+1+14+1+5 = 29 字符，未超过后端 order_no 的 String(32) 限制。
     * 序号仍保留（可读性与本地排序），但不再是唯一性来源。
     */
    buildOrderNo() {
      const d = new Date()
      const pad = (n, len = 2) => String(n).padStart(len, '0')
      const date = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`
      const time = `${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
      const key = 'pos_order_seq'
      const seq = (parseInt(localStorage.getItem(key) || '0', 10) + 1) % 100000
      localStorage.setItem(key, String(seq))
      return `${getDeviceId()}-${date}${time}-${pad(seq, 5)}`
    },

    /**
     * 持久化购物车到 localStorage
     */
    persistCart() {
      localStorage.setItem(LS_CART, JSON.stringify(this.cart))
    },
  },
})
