"""净额法唯一实现（Q05 / 拍板 3），供报表、班次汇总与会员统计三方复用。

=============================================================================
最终选定口径（B3 定稿，不是「建议」，不存在待决项）
=============================================================================
**「按订单关联、区间内订单统计退款」**：

1. 先按 ``Order.created_at ∈ [start, end)`` 且 ``Order.store_id == store_id``
   筛出订单集 ``O``（**不再按 ``status == "paid"`` 过滤**，退款后整单不再消失）；
2. 再取 ``O`` 中每笔订单关联的**全部** ``RefundRecord`` 金额之和，作为该订单的
   退款额映射 ``R = {order_id: SUM(refund_records.amount)}``；
   **不按退款单 ``created_at`` 是否落在区间过滤**；
3. ``net(o) = max(0, o.total_amount − R.get(o.id, 0))``，
   ``sales = Σ net(o)``，销售笔数 ``orders = count(O)``（部分退款仍计 1 笔）；
4. 商品排行 ``share(i) = i.amount × (net(o) / Σ明细金额)``：**保留所有未退商品行**，
   行不消失、金额按净额比例打折，不整单剔除。

选定理由（逐条对应上游约束）：

- **拍板 3「日报与交接班汇总数值完全一致」**：既有 ``ShiftService.summary()`` 的
  退款映射本就是 ``RefundRecord.order_id IN (班次订单 id)``、无退款时间过滤，
  本模块与之**逐字对齐**，并把 ``summary()`` 改为复用本模块，消除两套口径。
  若改用「退款单 created_at 落区间」，日报与班次在同一订单集上会算出不同数值。
- **避免跨区间重复扣减**：退款归属到原单所在区间（A.12 口径约束中提出的方案，
  此处定为最终口径）。若按退款单时间统计，昨天成交、今天退款的单会在
  「昨天」区间不扣、在「今天」区间被凭空扣成一笔负销售，且两日合计与该单净额不符。
- **A.12 唯一公式**：本模块是 ``refund_map`` / ``net_total`` / ``net_item_share``
  的唯一实现，任何调用方不得另写一套净额计算。

补充说明：金额一律 2 位小数（沿用现有 ``round(x, 2)`` 口径，列类型
``Numeric(12,2)`` 与全链路 Decimal 化随 PG / Q13 实施，B3 不改列类型）。
"""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, RefundRecord


def refund_map(
    db: Session,
    start: datetime,
    end: datetime,
    store_id: int,
    orders: list[Order] | None = None,
) -> dict[int, float]:
    """构造「订单 ID -> 该订单关联的全部退款额」映射（净额法唯一入口）。

    ``orders`` 由调用方传入时必须与其后用于 ``net_total`` / ``net_item_share``
    的订单集**完全相同**，以保证日报与班次汇总严格一致；未传入时按
    ``[start, end)`` 时间窗与 ``store_id`` 自行查询（查询条件与
    ``reports._window_orders`` 一致）。

    :param db: 数据库会话
    :param start: 查询区间开始（含，按订单 created_at）
    :param end: 查询区间结束（不含，按订单 created_at）
    :param store_id: 门店 ID
    :param orders: 已由调用方筛出的订单集；传入时跳过区间查询
    :return: ``{order_id: 累计退款额}``，无退款的订单不出现在映射中
    """
    if orders is None:
        orders = list(
            db.scalars(
                select(Order).where(
                    Order.store_id == store_id,
                    Order.created_at >= start,
                    Order.created_at < end,
                )
            ).all()
        )
    order_ids = [order.id for order in orders]
    result: dict[int, float] = {}
    if not order_ids:
        return result
    # 按订单关联统计：不按 refund_records.created_at 过滤，与 ShiftService 既有口径一致
    rows = db.execute(
        select(RefundRecord.order_id, RefundRecord.amount).where(
            RefundRecord.order_id.in_(order_ids)
        )
    ).all()
    for order_id, amount in rows:
        result[order_id] = result.get(order_id, 0.0) + float(amount or 0)
    return result


def net_order(order: Order, refund_map: dict[int, float]) -> float:
    """计算单笔订单净额：``max(0, 原单金额 − 该单累计退款额)``。

    :param order: 订单 ORM 对象
    :param refund_map: :func:`refund_map` 返回的退款映射
    :return: 该订单净额（不四舍五入到分，由聚合处统一 round）
    """
    refunded = float(refund_map.get(order.id, 0.0))
    return max(0.0, float(order.total_amount or 0) - refunded)


def net_total(orders: list[Order], refund_map: dict[int, float]) -> float:
    """汇总订单集的净销售额（部分退款仍计 1 笔，不剔除整单）。

    :param orders: 订单集（必须与构造 ``refund_map`` 时的订单集一致）
    :param refund_map: :func:`refund_map` 返回的退款映射
    :return: 净销售额（2 位小数），日报 / 班次 / 会员统计共用
    """
    return round(sum(net_order(order, refund_map) for order in orders), 2)


def net_item_share(rows: list, refund_map: dict[int, float]) -> list:
    """按净额把订单明细金额分摊为排行/毛利口径，保留全部未退商品行。

    公式（A.12）：``share(i) = i.amount × (net(o) / Σ明细金额)``。
    当订单明细合计为 0 时不做分摊（因子取 1.0），避免除零。

    :param rows: ``(OrderItem, Product, Category, Order)`` 结果行列表
    :param refund_map: :func:`refund_map` 返回的退款映射（订单集须覆盖 rows 内订单）
    :return: ``[(OrderItem, Product, Category, share)]`` 列表，行数与入参一致
    """
    order_sums: dict[int, float] = defaultdict(float)
    for item, _product, _category, order in rows:
        order_sums[order.id] += float(item.amount or 0)

    result: list = []
    for item, product, category, order in rows:
        base = order_sums[order.id]
        factor = net_order(order, refund_map) / base if base else 1.0
        share = round(float(item.amount or 0) * factor, 2)
        result.append((item, product, category, share))
    return result
