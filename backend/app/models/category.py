"""分类模型：商品两级分类。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    """商品分类表：支持两级分类（parent_id 为空的为一级分类）。"""

    __tablename__ = "categories"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 分类名称
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 上级分类 ID（空表示一级分类）
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    # 排序值（越小越靠前）
    sort: Mapped[int] = mapped_column(Integer, default=0)
    # 是否启用
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 预留门店 ID（多店扩展）
    store_id: Mapped[int] = mapped_column(Integer, default=1)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 子分类关联
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    # 上级分类关联
    parent: Mapped["Category | None"] = relationship(back_populates="children", remote_side=[id])
    # 分类下的商品关联
    products: Mapped[list["Product"]] = relationship(back_populates="category")
