"""门店库存服务：统一收口商品库存在各门店的读取与写入。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, ProductStock


class ProductStockService:
    """门店库存服务（静态方法），供商品、库存、同步与订单流程复用。

    商品档案已提升为租户级共享，库存以「商品 + 门店」为维度存放在
    product_stocks 表，本服务负责按门店取库存、按需建行与增减库存。
    """

    @staticmethod
    def get(db: Session, product_id: int, store_id: int) -> ProductStock | None:
        """查询指定商品在指定门店的库存记录。

        :param db: 数据库会话
        :param product_id: 商品 ID
        :param store_id: 门店 ID
        :return: 库存记录，不存在时返回 None
        """
        return db.scalar(
            select(ProductStock).where(
                ProductStock.product_id == product_id, ProductStock.store_id == store_id
            )
        )

    @staticmethod
    def get_map(db: Session, product_ids: list[int], store_id: int) -> dict[int, ProductStock]:
        """批量查询指定门店的库存记录，用于列表补充库存。

        :param db: 数据库会话
        :param product_ids: 商品 ID 列表
        :param store_id: 门店 ID
        :return: 商品 ID -> 库存记录
        """
        if not product_ids:
            return {}
        rows = db.scalars(
            select(ProductStock).where(
                ProductStock.product_id.in_(product_ids), ProductStock.store_id == store_id
            )
        ).all()
        return {row.product_id: row for row in rows}

    @staticmethod
    def get_or_create(db: Session, product: Product, store_id: int) -> ProductStock:
        """获取商品在指定门店的库存记录，不存在则创建零库存记录。

        :param db: 数据库会话
        :param product: 商品 ORM 对象
        :param store_id: 门店 ID
        :return: 库存记录
        """
        row = ProductStockService.get(db, product.id, store_id)
        if row is None:
            row = ProductStock(
                tenant_id=product.tenant_id,
                product_id=product.id,
                store_id=store_id,
                stock=0,
                safety_stock=0,
            )
            db.add(row)
        return row

    @staticmethod
    def apply(
        db: Session,
        product: Product,
        store_id: int,
        stock: float | None = None,
        safety_stock: float | None = None,
        delta: float | None = None,
    ) -> ProductStock:
        """更新指定门店库存：可设置库存绝对值、安全库存或按增量增减。

        :param db: 数据库会话
        :param product: 商品 ORM 对象
        :param store_id: 门店 ID
        :param stock: 库存绝对值（传入则覆盖）
        :param safety_stock: 安全库存绝对值（传入则覆盖）
        :param delta: 库存增量（正增负减，与 stock 互斥使用）
        :return: 更新后的库存记录
        """
        row = ProductStockService.get_or_create(db, product, store_id)
        if delta is not None:
            row.stock = round((row.stock or 0) + delta, 3)
        if stock is not None:
            row.stock = round(stock, 3)
        if safety_stock is not None:
            row.safety_stock = round(safety_stock, 3)
        return row

    @staticmethod
    def status(stock: float | None, safety_stock: float | None) -> str:
        """判断库存状态：ok=充足，low=低于安全库存，out=已售罄。

        :param stock: 当前库存
        :param safety_stock: 安全库存
        :return: 状态字符串
        """
        stock = stock or 0
        safety = safety_stock or 0
        if stock <= 0:
            return "out"
        if safety > 0 and stock < safety:
            return "low"
        return "ok"
