"""价格历史模型：商品调价留痕。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class ProductPriceHistory(Base):
    """商品价格变更历史表：记录每次调价的旧价/新价与操作人。"""

    __tablename__ = "product_price_history"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 关联商品
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id"), index=True, nullable=False
    )
    # 所属租户 ID
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 调价前价格
    old_price: Mapped[float] = mapped_column(Float, nullable=False)
    # 调价后价格
    new_price: Mapped[float] = mapped_column(Float, nullable=False)
    # 操作人用户 ID
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # 变更时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
