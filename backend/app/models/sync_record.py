"""同步记录模型：桌面端与服务端之间的数据同步状态。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class SyncRecord(Base):
    """数据同步记录表：记录下行（拉取）与上行（上传）的同步状态。"""

    __tablename__ = "sync_records"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 同步方向：down=服务端→收银端，up=收银端→服务端
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    # 同步目标（商品/订单/库存变动等）
    target: Mapped[str] = mapped_column(String(50), nullable=False)
    # 所属租户 ID
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 最近一次成功同步时间
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 待同步数量
    pending_count: Mapped[int] = mapped_column(Integer, default=0)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
