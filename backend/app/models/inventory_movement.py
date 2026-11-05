"""库存流水模型：入库/销售/盘点/报损的库存变动记录。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class InventoryMovement(Base):
    """库存变动流水表：追踪每次库存增减的来源与操作人。"""

    __tablename__ = "inventory_movements"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 关联商品
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id"), index=True, nullable=False
    )
    # 类型：inbound=入库，sale=销售，stocktake=盘点，breakage=报损
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    # 变动数量（按件商品）
    qty: Mapped[float] = mapped_column(Float, default=0)
    # 变动重量 kg（称重商品）
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 来源单据 ID（订单/入库单/盘点单等）
    ref_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # 操作人用户 ID
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # 预留门店 ID（多店扩展）
    store_id: Mapped[int] = mapped_column(Integer, default=1)
    # 是否已同步到服务端
    synced: Mapped[bool] = mapped_column(Boolean, default=False)
    # 变动时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
