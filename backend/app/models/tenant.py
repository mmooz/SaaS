"""租户模型：多租户 SaaS 的顶层组织单元，一个租户下可拥有多个门店。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class Tenant(Base):
    """租户表：每个独立经营主体（如一家连锁超市集团）为一个租户。"""

    __tablename__ = "tenants"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 租户名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 租户编码（唯一，用于标识）
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # 是否启用
    enabled: Mapped[bool] = mapped_column(default=True)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
