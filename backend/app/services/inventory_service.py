"""库存服务：库存变动入账、状态判定与销售自动扣减。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InventoryMovement, Product
from app.services.product_stock_service import ProductStockService

# Q14：前后端统一精度口径（B3 只统一 Python 层取整规则，不改任何列类型）。
#   - 重量 / 数量（kg、件）保留 3 位小数，与 POS 端 weight.toFixed(3) 一致；
#   - 金额（元）保留 2 位小数，沿用现有 round(x, 2) 口径，本批不改。
# 列类型 Numeric(10,3) / Numeric(12,2) 与整数分改造随 PG / Q13 批次实施。
# 该常量是库存重量取整的唯一来源，避免各调用点散落 magic number 3。
STOCK_PRECISION_DIGITS: int = 3
AMOUNT_PRECISION_DIGITS: int = 2


def round_stock(value: float | None) -> float:
    """按 Q14 统一口径取整重量 / 数量。

    :param value: 原始数值（可为 None）
    :return: 保留 3 位小数的浮点数
    """
    return round(float(value or 0), STOCK_PRECISION_DIGITS)


def round_amount(value: float | None) -> float:
    """按 Q14 统一口径取整金额。

    :param value: 原始数值（可为 None）
    :return: 保留 2 位小数的浮点数
    """
    return round(float(value or 0), AMOUNT_PRECISION_DIGITS)


class InventoryService:
    """库存业务服务（静态方法，供 API 与订单流程复用）。

    库存按门店隔离存放于 product_stocks 表，本服务所有变动都必须带门店 ID。
    """

    @staticmethod
    def status(stock: float | None, safety_stock: float | None) -> str:
        """判断库存状态：ok=充足，low=低于安全库存，out=已售罄。

        :param stock: 当前库存
        :param safety_stock: 安全库存
        :return: 状态字符串
        """
        return ProductStockService.status(stock, safety_stock)

    @staticmethod
    def record(
        db: Session,
        product: Product,
        movement_type: str,
        delta: float,
        store_id: int,
        ref_id: int | None = None,
        operator_id: int | None = None,
        apply_stock: bool = True,
        tenant_id: int | None = None,
    ) -> InventoryMovement:
        """写入一条库存流水并按需同步门店库存。

        :param db: 数据库会话
        :param product: 商品 ORM 对象
        :param movement_type: inbound/sale/stocktake/breakage/refund
        :param delta: 库存变动量（正增负减）
        :param store_id: 发生门店 ID（库存按门店隔离）
        :param ref_id: 来源单据 ID
        :param operator_id: 操作人 ID
        :param apply_stock: 是否同时更新门店库存（盘点时由调用方直接赋值）
        :param tenant_id: 所属租户 ID（多租户隔离用）
        :return: 库存流水对象
        """
        if tenant_id is None:
            raise ValueError("库存流水必须指定 tenant_id")
        # 称重商品记重量，按件商品记件数
        is_weighed = product.pricing_mode == "weigh"
        movement = InventoryMovement(
            tenant_id=tenant_id,
            product_id=product.id,
            type=movement_type,
            qty=0 if is_weighed else round_stock(delta),
            weight_kg=round_stock(delta) if is_weighed else None,
            ref_id=ref_id,
            operator_id=operator_id,
            store_id=store_id,
            synced=True,
        )
        if apply_stock:
            ProductStockService.apply(db, product, store_id, delta=delta)
        db.add(movement)
        return movement

    @staticmethod
    def deduct_for_order(db: Session, order) -> None:
        """订单成交后按明细自动扣减门店库存并写入销售流水。

        :param db: 数据库会话
        :param order: 订单 ORM 对象（含 items）
        """
        # 一次性取出涉及的商品，避免逐条查询
        product_ids = [i.product_id for i in order.items if i.product_id]
        if not product_ids:
            return
        products = {
            p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
        }
        for item in order.items:
            product = products.get(item.product_id)
            if not product:
                continue
            # 多单位按件商品按基础单位数量（base_qty = qty × factor）扣减；
            # 称重商品按重量；未传递 base_qty 的按件商品回退到 qty
            if item.is_weighted:
                delta = -(item.weight_kg or 0)
            else:
                delta = -(item.base_qty if item.base_qty is not None else item.qty)
            InventoryService.record(
                db,
                product,
                "sale",
                delta,
                store_id=order.store_id,
                ref_id=order.id,
                operator_id=order.cashier_id,
                tenant_id=order.tenant_id,
            )

    @staticmethod
    def restore_for_refund(db: Session, order, items) -> None:
        """退款后按退货明细回滚门店库存并写入退款流水。

        :param db: 数据库会话
        :param order: 原订单 ORM 对象
        :param items: 本次退货的订单明细列表
        """
        # 一次性取出涉及的商品，避免逐条查询
        product_ids = [i.product_id for i in items if i.product_id]
        if not product_ids:
            return
        products = {
            p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
        }
        for item in items:
            product = products.get(item.product_id)
            if not product:
                continue
            # 退货量为正，库存加回；多单位按件按 base_qty 回滚
            if item.is_weighted:
                delta = item.weight_kg or 0
            else:
                delta = item.base_qty if item.base_qty is not None else item.qty
            InventoryService.record(
                db,
                product,
                "refund",
                delta,
                store_id=order.store_id,
                ref_id=order.id,
                operator_id=order.cashier_id,
                tenant_id=order.tenant_id,
            )
