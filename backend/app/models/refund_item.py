"""退款明细模型：退款单内的每个退货商品行。"""

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.snowflake import next_id


class RefundItem(Base):
    """退款明细表：记录被退商品的原明细、数量/重量与退款金额。"""

    __tablename__ = "refund_items"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 所属退款单
    refund_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("refund_records.id"), index=True, nullable=False
    )
    # 原订单明细主键（用于避免同一行重复退货）
    order_item_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    # 商品名称（快照）
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # 退货数量（按件商品）
    qty: Mapped[int] = mapped_column(Integer, default=1)
    # 退货重量 kg（称重商品）
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 退款金额
    amount: Mapped[float] = mapped_column(Float, default=0)
    # 是否称重商品
    is_weighted: Mapped[bool] = mapped_column(Boolean, default=False)

    # 所属退款单关联
    refund: Mapped["RefundRecord"] = relationship(back_populates="items")
