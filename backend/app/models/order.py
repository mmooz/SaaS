"""订单模型：收银端上传的销售订单。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    """订单表：一笔结算的完整记录，含支付方式明细与状态流转。"""

    __tablename__ = "orders"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 订单号（唯一，收银端生成，用于幂等上传）
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    # 预留门店 ID（多店扩展）
    store_id: Mapped[int] = mapped_column(Integer, default=1)
    # 收银员用户 ID
    cashier_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 交接班会话 ID
    shift_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 订单状态：pending=进行中，paid=已结算，refunded=已退款
    status: Mapped[str] = mapped_column(String(16), default="paid")
    # 应收总额
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    # 优惠金额
    discount_amount: Mapped[float] = mapped_column(Float, default=0)
    # 支付方式明细（JSON：{现金: x, 微信: y, ...}）
    pay_details: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # 关联会员
    member_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 备注
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 是否已同步到服务端
    synced: Mapped[bool] = mapped_column(default=False)
    # 下单时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 订单明细关联
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
