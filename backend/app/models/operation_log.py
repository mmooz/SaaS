"""操作日志模型：关键操作留痕。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class OperationLog(Base):
    """操作日志表：记录登录、调价、退款、盘点等关键操作。"""

    __tablename__ = "operation_logs"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 操作人用户 ID
    operator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # 操作动作（如 调价/退款/盘点/登录）
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # 操作详情（JSON 或文本）
    detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # 操作时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
