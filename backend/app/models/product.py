"""商品模型：收银端与后台共用的商品档案。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    """商品表：包含称重/按件两种计价方式，含价格、库存与生鲜属性。"""

    __tablename__ = "products"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 商品条码（唯一，含生鲜店内码）
    barcode: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    # 商品名称
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # 拼音码（用于快速检索）
    pinyin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 所属分类
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    # 计价方式：weigh=按重量称重，count=按件
    pricing_mode: Mapped[str] = mapped_column(String(10), default="weigh")
    # 计量单位（kg/g/个/袋/盒/瓶）
    unit: Mapped[str] = mapped_column(String(10), default="kg")
    # 零售单价
    price: Mapped[float] = mapped_column(Float, default=0)
    # 会员单价（可空）
    member_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 进价（用于毛利统计）
    cost_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 保质期天数（生鲜属性）
    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 是否默认打印价格标签
    label_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 当前库存（称重商品为重量 kg，按件商品为件数）
    stock: Mapped[float] = mapped_column(Float, default=0)
    # 安全库存（低于此值预警）
    safety_stock: Mapped[float] = mapped_column(Float, default=0)
    # 是否启用（停用后收银端不可售）
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 预留门店 ID（多店扩展）
    store_id: Mapped[int] = mapped_column(Integer, default=1)
    # 创建与更新时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 分类关联
    category: Mapped["Category | None"] = relationship(back_populates="products")
