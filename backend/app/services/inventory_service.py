"""库存服务：库存变动入账、状态判定与销售自动扣减。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InventoryMovement, Product


class InventoryService:
    """库存业务服务（静态方法，供 API 与订单流程复用）。"""

    @staticmethod
    def status(product: Product) -> str:
        """判断库存状态：ok=充足，low=低于安全库存，out=已售罄。

        :param product: 商品 ORM 对象
        :return: 状态字符串
        """
        stock = product.stock or 0
        safety = product.safety_stock or 0
        if stock <= 0:
            return "out"
        if safety > 0 and stock < safety:
            return "low"
        return "ok"

    @staticmethod
    def record(
        db: Session,
        product: Product,
        movement_type: str,
        delta: float,
        ref_id: int | None = None,
        operator_id: int | None = None,
        apply_stock: bool = True,
    ) -> InventoryMovement:
        """写入一条库存流水并按需同步商品库存。

        :param db: 数据库会话
        :param product: 商品 ORM 对象
        :param movement_type: inbound/sale/stocktake/breakage
        :param delta: 库存变动量（正增负减）
        :param ref_id: 来源单据 ID
        :param operator_id: 操作人 ID
        :param apply_stock: 是否同时更新商品库存（盘点时由调用方直接赋值）
        :return: 库存流水对象
        """
        # 称重商品记重量，按件商品记件数
        is_weighed = product.pricing_mode == "weigh"
        movement = InventoryMovement(
            product_id=product.id,
            type=movement_type,
            qty=0 if is_weighed else round(delta, 3),
            weight_kg=round(delta, 3) if is_weighed else None,
            ref_id=ref_id,
            operator_id=operator_id,
            store_id=product.store_id or 1,
            synced=True,
        )
        if apply_stock:
            product.stock = round((product.stock or 0) + delta, 3)
        db.add(movement)
        return movement

    @staticmethod
    def deduct_for_order(db: Session, order) -> None:
        """订单成交后按明细自动扣减库存并写入销售流水。

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
            delta = -(item.weight_kg or 0) if item.is_weighted else -item.qty
            InventoryService.record(
                db, product, "sale", delta, ref_id=order.id, operator_id=order.cashier_id
            )

    @staticmethod
    def restore_for_refund(db: Session, order, items) -> None:
        """退款后按退货明细回滚库存并写入退款流水。

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
            # 退货量为正，库存加回
            delta = (item.weight_kg or 0) if item.is_weighted else item.qty
            InventoryService.record(
                db, product, "refund", delta, ref_id=order.id, operator_id=order.cashier_id
            )
