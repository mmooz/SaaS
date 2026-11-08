"""订单明细模型：订单内的每个商品行。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.snowflake import next_id


class OrderItem(Base):
    """订单明细表：记录商品、数量/重量、单价与金额，标记称重商品。"""

    __tablename__ = "order_items"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 所属订单
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id"), index=True, nullable=False
    )
    # 所属租户 ID（从订单继承，冗余便于按租户直接过滤）
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 商品 ID（可空：商品删除后仍保留快照）
    product_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # 商品名称（快照，避免商品改名影响历史订单）
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # 数量（按件商品）：Q14 前后端统一 3 位小数口径；列类型 Numeric(10,3) 随 PG / Q13
    qty: Mapped[int] = mapped_column(Integer, default=1)
    # 重量 kg（称重商品）：Q14 前后端统一 3 位小数口径（0.005kg 分度不被抹平）；
    # 列类型 Numeric(10,3) 随 PG / Q13，B3 不改列定义
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 成交单价：金额统一 2 位小数；列类型 Numeric(12,2) 随 PG / Q13
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    # 行金额：金额统一 2 位小数；列类型 Numeric(12,2) 随 PG / Q13
    amount: Mapped[float] = mapped_column(Float, default=0)
    # 行优惠金额
    discount_amount: Mapped[float] = mapped_column(Float, default=0)
    # 是否称重商品
    is_weighted: Mapped[bool] = mapped_column(Boolean, default=False)
    # 是否已打印价格标签
    label_printed: Mapped[bool] = mapped_column(Boolean, default=False)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 所属订单关联
    order: Mapped["Order"] = relationship(back_populates="items")
