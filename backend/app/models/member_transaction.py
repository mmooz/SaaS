"""会员流水模型：储值、消费、退款与积分变动的明细。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MemberTransaction(Base):
    """会员资金/积分流水表：记录每次充值与消费变动。"""

    __tablename__ = "member_transactions"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 关联会员
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True, nullable=False)
    # 类型：recharge=充值，consume=消费，refund=退款，points=积分变动
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    # 金额变动（正/负）
    amount: Mapped[float] = mapped_column(Float, default=0)
    # 积分变动（正/负）
    points: Mapped[int] = mapped_column(Integer, default=0)
    # 操作人用户 ID
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 流水时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
