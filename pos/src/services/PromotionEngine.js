// 促销规则引擎：在收银端计算单品优惠价与整单满减金额

/**
 * 金额保留两位小数
 * @param {number} value 原始金额
 * @returns {number} 两位小数金额
 */
function round2(value) {
  return +value.toFixed(2)
}

/**
 * 促销规则引擎（纯函数集合，供收银台与状态层复用）
 */
export class PromotionEngine {
  /**
   * 判断促销规则是否作用于某购物车商品
   * @param {object} promo 促销规则
   * @param {object} item 购物车商品（含 productId / categoryId）
   * @returns {boolean} 是否命中
   */
  static inScope(promo, item) {
    // 指定商品列表优先匹配
    if (promo.product_ids && promo.product_ids.length) {
      return promo.product_ids.includes(item.productId)
    }
    // 其次按分类匹配
    if (promo.category_ids && promo.category_ids.length) {
      return promo.category_ids.includes(item.categoryId)
    }
    // 两者都未指定视为全场适用
    return true
  }

  /**
   * 计算商品在促销下的优惠单价（特价或折扣价）
   * @param {object} item 购物车商品
   * @param {Array<object>} promotions 生效促销列表
   * @returns {number|null} 优惠单价，无可用促销返回 null
   */
  static promoPrice(item, promotions) {
    let best = null
    for (const promo of promotions || []) {
      if (!PromotionEngine.inScope(promo, item)) continue
      const params = promo.params || {}
      if (promo.type === 'special' && typeof params.price === 'number') {
        // 限时特价：直接使用特价单价
        if (best === null || params.price < best) best = params.price
      } else if (promo.type === 'discount' && typeof params.rate === 'number') {
        // 折扣：零售价 × 折扣率
        const discounted = round2(item.price * params.rate)
        if (best === null || discounted < best) best = discounted
      }
    }
    return best
  }

  /**
   * 计算商品成交单价：零售价、会员价与促销价取最低
   * @param {object} item 购物车商品
   * @param {Array<object>} promotions 生效促销列表
   * @param {object|null} member 当前会员
   * @returns {number} 成交单价
   */
  static itemPrice(item, promotions, member) {
    const candidates = [item.price]
    if (member && item.memberPrice) candidates.push(item.memberPrice)
    const promo = PromotionEngine.promoPrice(item, promotions)
    if (promo !== null) candidates.push(promo)
    return Math.min(...candidates)
  }

  /**
   * 计算整单满减金额（多个满减规则取优惠最大的一项）
   * @param {number} subtotal 单品结算小计
   * @param {Array<object>} promotions 生效促销列表
   * @returns {number} 满减优惠金额
   */
  static orderDiscount(subtotal, promotions) {
    let best = 0
    for (const promo of promotions || []) {
      if (promo.type !== 'full_reduce') continue
      const params = promo.params || {}
      const threshold = Number(params.threshold) || 0
      const reduce = Number(params.reduce) || 0
      if (threshold > 0 && subtotal >= threshold && reduce > best) best = reduce
    }
    // 满减金额不应超过小计
    return round2(Math.min(best, subtotal))
  }
}
