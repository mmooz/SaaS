"""用户模型：收银员/店长/管理员账号。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class User(Base):
    """系统用户表：角色决定权限（super=平台超级管理员，admin=租户管理员，manager=店长，cashier=收银员）。"""

    __tablename__ = "users"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 所属租户 ID
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 登录用户名（租户内唯一）
    username: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    # 密码哈希
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # 姓名
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 角色：super=平台超级管理员（跨租户管理），admin=租户管理员，manager=店长，cashier=收银员
    role: Mapped[str] = mapped_column(String(10), default="cashier")
    # 是否启用
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
