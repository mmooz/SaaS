"""会员模型：会员档案与储值/积分余额。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class Member(Base):
    """会员表：手机号唯一建档，含等级、积分与储值余额。"""

    __tablename__ = "members"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 手机号（唯一，快速建档）
    mobile: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    # 姓名
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 等级：normal=普通，silver=银卡，gold=金卡
    level: Mapped[str] = mapped_column(String(10), default="normal")
    # 积分余额
    points: Mapped[int] = mapped_column(Integer, default=0)
    # 储值余额（元）
    balance: Mapped[float] = mapped_column(Float, default=0)
    # 累计消费金额
    total_spent: Mapped[float] = mapped_column(Float, default=0)
    # 预留门店 ID（多店扩展）
    store_id: Mapped[int] = mapped_column(Integer, default=1)
    # 创建与更新时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
