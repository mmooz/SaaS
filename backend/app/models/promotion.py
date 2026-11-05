"""促销模型：限时特价、折扣、满减满赠规则。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class Promotion(Base):
    """促销规则表：按类型存储优惠参数（JSON），收银端规则引擎应用。"""

    __tablename__ = "promotions"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 类型：special=限时特价，discount=折扣，full_reduce=满减满赠
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    # 促销名称
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # 适用商品 ID 列表（JSON 数组）
    product_ids: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # 适用分类 ID 列表（JSON 数组）
    category_ids: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # 优惠参数（JSON：特价价格/折扣率/满X减Y等）
    params: Mapped[str] = mapped_column(String(1024), nullable=False)
    # 生效开始时间
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 生效结束时间
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 是否启用
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 预留门店 ID（多店扩展）
    store_id: Mapped[int] = mapped_column(Integer, default=1)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
