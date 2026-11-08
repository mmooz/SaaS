"""商品模型：收银端与后台共用的商品档案。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.snowflake import next_id


class Product(Base):
    """商品表：包含称重/按件两种计价方式，含价格、库存与生鲜属性。"""

    __tablename__ = "products"
    # 表级约束：条码在同租户内唯一，不同租户可使用相同条码
    # Q18（B3 过渡方案）：SQLite 不支持部分唯一索引，软删行仍会占用该唯一键。
    # 删除商品与导入命中历史软删行时由应用层把其 barcode 改写为 D{id} 释放占用
    # （见 api/products.py 与 services/excel_service.py）；PG baseline 改为部分
    # 唯一索引 WHERE deleted = false 后可移除过渡逻辑。B3 不改索引定义、不改列宽。
    __table_args__ = (
        Index("uq_products_tenant_barcode", "tenant_id", "barcode", unique=True),
    )

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 商品条码（同租户内唯一，含生鲜店内码）
    # Q18：软删行改写为 D{id}（≤20 字符），仍落在 String(32) 内，无需扩容；
    # Q32-5 的 String(32) 列宽调整随 PG 批次，B3 保持现有列定义不动。
    barcode: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    # 商品名称
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # 拼音码（用于快速检索）
    pinyin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 所属分类
    category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id"), nullable=True
    )
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
    # 是否已删除（软删除标记，删除后不再参与任何业务查询，数据保留可追溯）
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
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

    # 分类关联
    category: Mapped["Category | None"] = relationship(back_populates="products")
