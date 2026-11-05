// POS 收银状态管理（Pinia）：商品缓存、购物车、订单上传与离线队列

import { defineStore } from 'pinia'
import { fetchSyncData, uploadOrder } from '../api'

// localStorage 键名
const LS_PRODUCTS = 'pos_products' // 商品本地缓存（离线可用）
const LS_CART = 'pos_cart' // 购物车本地缓存
const LS_HANG = 'pos_hang_orders' // 挂单本地缓存
const LS_OFFLINE = 'pos_offline_orders' // 待上传订单队列

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
    categories: loadLS('pos_categories', []),
    // 同步状态：idle/syncing/synced/error
    syncState: 'idle',
    syncError: '',
    lastSyncTime: null,
    // 当前收银员
    cashier: null,
    // 购物车
    cart: loadLS(LS_CART, []),
    // 挂单列表
    hangOrders: loadLS(LS_HANG, []),
    // 待上传订单队列
    offlineOrders: loadLS(LS_OFFLINE, []),
  }),

  getters: {
    // 购物车应收合计
    totalAmount(state) {
      return state.cart.reduce((sum, i) => sum + i.amount, 0)
    },
    // 购物车商品数
    cartCount(state) {
      return state.cart.length
    },
    // 是否有待上传的离线订单
    hasOfflineOrders(state) {
      return state.offlineOrders.length > 0
    },
  },

  actions: {
    /**
     * 同步拉取商品与分类（覆盖本地缓存）
     */
    async syncProducts() {
      this.syncState = 'syncing'
      try {
        const data = await fetchSyncData(this.lastSyncTime)
        if (data.products.length) {
          this.products = data.products
          localStorage.setItem(LS_PRODUCTS, JSON.stringify(this.products))
        }
        if (data.categories.length) {
          this.categories = data.categories
          localStorage.setItem('pos_categories', JSON.stringify(this.categories))
        }
        this.lastSyncTime = data.server_time
        this.syncState = 'synced'
        this.syncError = ''
      } catch (err) {
        this.syncState = 'error'
        this.syncError = err.message
      }
    },

    /**
     * 设置当前收银员
     */
    setCashier(user) {
      this.cashier = user
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
     * 结算：生成订单号并上传服务端；失败则进入离线队列
     * @param {object} payload { payMethod, cashReceived, memberId, remark }
     * @returns {Promise<boolean>} 是否上传成功
     */
    async settle(payload) {
      const orderNo = this.buildOrderNo()
      const payDetails = JSON.stringify({ [payload.payMethod]: this.totalAmount })
      const order = {
        order_no: orderNo,
        cashier_id: this.cashier ? this.cashier.id : null,
        status: 'paid',
        total_amount: +this.totalAmount.toFixed(2),
        discount_amount: 0,
        pay_details: payDetails,
        member_id: payload.memberId || null,
        items: this.cart.map((i) => ({
          product_id: i.productId,
          name: i.name,
          qty: i.qty,
          weight_kg: i.weighted ? i.weight : null,
          unit_price: i.price,
          amount: i.amount,
          is_weighted: i.weighted,
          label_printed: i.weighted,
        })),
      }
      try {
        await uploadOrder(order)
        this.clearCart()
        return true
      } catch (err) {
        // 上传失败：进入离线队列，本地保留待重传
        this.offlineOrders.push(order)
        localStorage.setItem(LS_OFFLINE, JSON.stringify(this.offlineOrders))
        this.clearCart()
        return false
      }
    },

    /**
     * 重传离线订单队列
     */
    async flushOfflineOrders() {
      const pending = [...this.offlineOrders]
      for (const order of pending) {
        try {
          await uploadOrder(order)
          this.offlineOrders = this.offlineOrders.filter((o) => o.order_no !== order.order_no)
        } catch {
          break // 网络仍不可用，停止重传
        }
      }
      localStorage.setItem(LS_OFFLINE, JSON.stringify(this.offlineOrders))
    },

    /**
     * 生成本地订单号：yyyyMMdd-HHmmss-序号（含时间戳避免与历史订单冲突）
     */
    buildOrderNo() {
      const d = new Date()
      const pad = (n) => String(n).padStart(2, '0')
      const date = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`
      const time = `${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
      const key = 'pos_order_seq'
      const seq = (parseInt(localStorage.getItem(key) || '0', 10) + 1) % 100000
      localStorage.setItem(key, String(seq))
      return `${date}-${time}-${String(seq).padStart(5, '0')}`
    },

    /**
     * 持久化购物车到 localStorage
     */
    persistCart() {
      localStorage.setItem(LS_CART, JSON.stringify(this.cart))
    },
  },
})
