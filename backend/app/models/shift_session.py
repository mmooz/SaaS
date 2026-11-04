"""交接班模型：收银员班次与会话。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ShiftSession(Base):
    """交接班会话表：记录每班收银员的销售汇总与现金交接。"""

    __tablename__ = "shift_sessions"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 收银员用户 ID
    cashier_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    # 预留门店 ID（多店扩展）
    store_id: Mapped[int] = mapped_column(Integer, default=1)
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
