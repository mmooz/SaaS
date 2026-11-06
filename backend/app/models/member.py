"""会员模型：会员档案与储值/积分余额。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class Member(Base):
    """会员表：手机号唯一建档，含等级、积分与储值余额。"""

    __tablename__ = "members"
    # 表级约束：手机号在同租户内唯一，不同租户可共用同一手机号
    __table_args__ = (
        Index("uq_members_tenant_mobile", "tenant_id", "mobile", unique=True),
    )

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 手机号（同租户内唯一，快速建档）
    mobile: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
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
    # 所属租户 ID
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 所属门店 ID
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id"), index=True, nullable=False
    )
    # 创建与更新时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
