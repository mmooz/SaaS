"""门店模型：租户下的具体经营门店，一个租户可拥有多个门店。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class Store(Base):
    """门店表：归属某个租户，承载商品、订单、库存等业务数据。"""

    __tablename__ = "stores"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 所属租户
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 门店名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 门店地址
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 联系电话
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # 是否启用
    enabled: Mapped[bool] = mapped_column(default=True)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
