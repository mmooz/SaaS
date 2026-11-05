"""系统设置模型：按分组保存门店信息与收银参数（键值 + JSON 文本）。"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemSetting(Base):
    """系统设置表：group 为设置分组（store=门店信息，cashier=收银参数），value 为 JSON 文本。"""

    __tablename__ = "system_settings"

    # 设置分组（主键，如 store / cashier）
    group: Mapped[str] = mapped_column(String(50), primary_key=True)
    # 分组设置内容（JSON 文本）
    value: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # 最后更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
