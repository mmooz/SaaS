"""订单明细模型：订单内的每个商品行。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderItem(Base):
    """订单明细表：记录商品、数量/重量、单价与金额，标记称重商品。"""

    __tablename__ = "order_items"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 所属订单
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    # 商品 ID（可空：商品删除后仍保留快照）
    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 商品名称（快照，避免商品改名影响历史订单）
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # 数量（按件商品）
    qty: Mapped[int] = mapped_column(Integer, default=1)
    # 重量 kg（称重商品）
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 成交单价
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    # 行金额
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
