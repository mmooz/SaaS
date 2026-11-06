"""收银端数据同步 API：商品/分类增量下发。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_store_id, get_tenant_id
from app.models import Category, Product
from app.schemas.category_out import CategoryOut
from app.schemas.product_out import ProductOut
from app.services.product_stock_service import ProductStockService

# 同步路由
router = APIRouter(prefix="/api/sync", tags=["数据同步"])


@router.get("/products", response_model=dict)
def sync_products(
    after: datetime | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """增量拉取商品与分类：返回 after 时间之后变更的数据，用于收银端本地缓存更新。

    商品与分类为租户级共享，库存取当前门店；首次同步不传 after，返回全量数据。
    """
    # 商品：按更新时间过滤（SQLite 使用 naive datetime 比较），已删除商品不下发
    product_stmt = select(Product).where(
        Product.tenant_id == tenant_id, Product.deleted.is_(False)
    )
    if after:
        product_stmt = product_stmt.where(Product.updated_at > after)
    products = db.scalars(product_stmt.order_by(Product.id)).all()
    product_list = [ProductOut.model_validate(p) for p in products]
    stocks = ProductStockService.get_map(db, [p.id for p in products], store_id)
    for out, product in zip(product_list, products):
        out.category_name = product.category.name if product.category else None
        # 库存按当前门店下发
        row = stocks.get(product.id)
        out.stock = round(row.stock or 0, 3) if row else 0
        out.safety_stock = (row.safety_stock or 0) if row else 0

    # 分类：全量下发（数量少，保持树结构一致）
    categories = db.scalars(
        select(Category)
        .where(Category.tenant_id == tenant_id)
        .order_by(Category.sort, Category.id)
    ).all()
    # 显式构造（children 置空），避免 ORM relationship 自动递归填充冗余子树
    category_list = [
        CategoryOut(
            id=c.id,
            name=c.name,
            parent_id=c.parent_id,
            sort=c.sort,
            enabled=c.enabled,
            store_id=c.store_id,
            created_at=c.created_at,
            children=[],
        )
        for c in categories
    ]

    return {
        "products": product_list,
        "categories": category_list,
        "server_time": datetime.now().isoformat(),
    }
