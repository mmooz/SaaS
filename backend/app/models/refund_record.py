"""退款记录模型：一笔退款单的主记录。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RefundRecord(Base):
    """退款单表：记录整单退款或单项退货的金额、原因与操作人。"""

    __tablename__ = "refund_records"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 退款单号（唯一，收银端生成）
    refund_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    # 原订单主键
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    # 原订单号（冗余保存，便于查询展示）
    order_no: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    # 退款类型：full=整单退款，item=单项退货
    refund_type: Mapped[str] = mapped_column(String(10), default="full")
    # 退款金额
    amount: Mapped[float] = mapped_column(Float, default=0)
    # 退款原因
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 操作收银员用户 ID
    cashier_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 店长授权人用户 ID（非本人订单退款时记录）
    authorizer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 退款时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 退款明细关联
    items: Mapped[list["RefundItem"]] = relationship(
        back_populates="refund", cascade="all, delete-orphan"
    )
