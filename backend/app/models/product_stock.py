"""门店库存模型：商品档案租户级共享后，库存按门店独立存放。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class ProductStock(Base):
    """门店库存表：记录同一商品在各门店的库存与安全库存。

    商品档案（products）已提升为租户级共享，库存必须按门店隔离，
    因此把库存从商品行拆出，以「商品 + 门店」为维度单独存放。
    """

    __tablename__ = "product_stocks"
    # 表级约束：同一商品在同一门店只有一条库存记录
    __table_args__ = (
        Index("uq_product_stocks_product_store", "product_id", "store_id", unique=True),
    )

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 关联商品 ID
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id"), index=True, nullable=False
    )
    # 所属租户 ID
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 所属门店 ID
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id"), index=True, nullable=False
    )
    # 当前库存（称重商品为重量 kg，按件商品为件数）
    stock: Mapped[float] = mapped_column(Float, default=0)
    # 安全库存（低于此值预警）
    safety_stock: Mapped[float] = mapped_column(Float, default=0)
    # 创建与更新时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
