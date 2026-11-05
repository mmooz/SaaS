"""分类模型：商品两级分类。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.snowflake import next_id


class Category(Base):
    """商品分类表：支持两级分类（parent_id 为空的为一级分类）。"""

    __tablename__ = "categories"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 分类名称
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 上级分类 ID（空表示一级分类）
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id"), nullable=True
    )
    # 排序值（越小越靠前）
    sort: Mapped[int] = mapped_column(Integer, default=0)
    # 是否启用
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 所属租户 ID
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # 所属门店 ID
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id"), index=True, nullable=False
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 子分类关联
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    # 上级分类关联
    parent: Mapped["Category | None"] = relationship(back_populates="children", remote_side=[id])
    # 分类下的商品关联
    products: Mapped[list["Product"]] = relationship(back_populates="category")
