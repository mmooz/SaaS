"""交接班模型：收银员班次与会话。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class ShiftSession(Base):
    """交接班会话表：记录每班收银员的销售汇总与现金交接。"""

    __tablename__ = "shift_sessions"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 收银员用户 ID
    cashier_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    # 所属租户 ID
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 所属门店 ID
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id"), index=True, nullable=False
    )
    # 接班时间
    start_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # 交班时间（空表示未交班）
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 现金底金
    base_cash: Mapped[float] = mapped_column(Float, default=0)
    # 本班销售额
    total_sales: Mapped[float] = mapped_column(Float, default=0)
    # 本班订单数
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    # 状态：open=进行中，closed=已交班
    status: Mapped[str] = mapped_column(String(10), default="open")
