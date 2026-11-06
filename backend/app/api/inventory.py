"""库存管理 API：库存查询/预警、入库、盘点、报损与变动流水。

商品档案为租户级共享，库存按门店隔离存放在 product_stocks 表，
因此本模块所有查询与写入都会带上当前门店。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_manager_user, get_store_id, get_tenant_id
from app.models import InventoryMovement, Product, ProductStock, User
from app.schemas.inventory_breakage import InventoryBreakage
from app.schemas.inventory_inbound import InventoryInbound
from app.schemas.inventory_movement_out import InventoryMovementOut
from app.schemas.inventory_stocktake import InventoryStocktake
from app.services.inventory_service import InventoryService
from app.services.product_stock_service import ProductStockService

# 库存路由
router = APIRouter(prefix="/api/inventory", tags=["库存管理"])


def _get_product(db: Session, product_id: int, tenant_id: int) -> Product:
    """按主键取商品并校验归属当前租户，不存在则抛 404。

    :param db: 数据库会话
    :param product_id: 商品 ID
    :param tenant_id: 当前租户 ID
    :return: 商品 ORM 对象
    """
    product = db.scalar(
        select(Product).where(
            Product.id == product_id, Product.tenant_id == tenant_id, Product.deleted.is_(False)
        )
    )
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


def _item(product: Product, stock: ProductStock | None) -> dict:
    """把商品与门店库存转为库存列表项。

    :param product: 商品 ORM 对象
    :param stock: 当前门店库存记录（可能不存在）
    :return: 库存展示字典
    """
    current = round(stock.stock or 0, 3) if stock else 0
    safety = (stock.safety_stock or 0) if stock else 0
    return {
        "product_id": product.id,
        "barcode": product.barcode,
        "name": product.name,
        "category": product.category.name if product.category else None,
        "unit": product.unit,
        "pricing_mode": product.pricing_mode,
        "stock": current,
        "safety_stock": safety,
        "cost_price": product.cost_price,
        "status": InventoryService.status(current, safety),
        "updated_at": stock.updated_at if stock else product.updated_at,
    }


def _stock_join(stmt, store_id: int):
    """给商品查询挂上当前门店的库存记录（左连接，无库存时按 0 处理）。

    :param stmt: 商品查询语句
    :param store_id: 当前门店 ID
    :return: 带库存连接与列的查询语句
    """
    return stmt.outerjoin(
        ProductStock,
        and_(ProductStock.product_id == Product.id, ProductStock.store_id == store_id),
    )


@router.get("", response_model=dict)
def list_inventory(
    keyword: str | None = None,
    category_id: int | None = None,
    low_only: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """分页查询库存：商品租户级共享，库存取当前门店，不含已删除商品。"""
    stmt = _stock_join(
        select(Product, ProductStock).where(
            Product.tenant_id == tenant_id, Product.deleted.is_(False)
        ),
        store_id,
    )
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Product.name.like(like), Product.barcode.like(like)))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if low_only:
        stock = func.coalesce(ProductStock.stock, 0)
        safety = func.coalesce(ProductStock.safety_stock, 0)
        stmt = stmt.where(or_(stock <= 0, and_(safety > 0, stock < safety)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(Product.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_item(product, stock) for product, stock in rows],
    }


@router.get("/alerts", response_model=dict)
def list_alerts(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """库存预警：返回当前门店已售罄或低于安全库存的商品清单。"""
    stock = func.coalesce(ProductStock.stock, 0)
    safety = func.coalesce(ProductStock.safety_stock, 0)
    rows = db.execute(
        _stock_join(
            select(Product, ProductStock).where(
                Product.tenant_id == tenant_id, Product.deleted.is_(False)
            ),
            store_id,
        )
        .where(or_(stock <= 0, and_(safety > 0, stock < safety)))
        .order_by(stock)
    ).all()
    return {"total": len(rows), "items": [_item(product, stock_row) for product, stock_row in rows]}


@router.post("/inbound", response_model=dict)
def inbound(
    data: InventoryInbound,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """采购入库：增加门店库存、可选更新进价并写入入库流水。"""
    product = _get_product(db, data.product_id, tenant_id)
    # 传入进价时同步更新商品进价（商品档案租户级共享）
    if data.cost_price is not None:
        product.cost_price = data.cost_price
    InventoryService.record(
        db,
        product,
        "inbound",
        data.qty,
        store_id=store_id,
        operator_id=data.operator_id,
        tenant_id=tenant_id,
    )
    db.commit()
    db.refresh(product)
    stock = ProductStockService.get(db, product.id, store_id)
    return {
        "message": "入库成功",
        "product_id": product.id,
        "stock": round(stock.stock or 0, 3) if stock else 0,
    }


@router.post("/stocktake", response_model=dict)
def stocktake(
    data: InventoryStocktake,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """盘点：以实盘数覆盖当前门店库存并记录差异流水。"""
    product = _get_product(db, data.product_id, tenant_id)
    stock_row = ProductStockService.get_or_create(db, product, store_id)
    current = stock_row.stock or 0
    diff = round(data.actual - current, 3)
    # 差异为零也记录盘点流水，便于追溯
    InventoryService.record(
        db,
        product,
        "stocktake",
        diff,
        store_id=store_id,
        operator_id=data.operator_id,
        apply_stock=False,
        tenant_id=tenant_id,
    )
    stock_row.stock = round(data.actual, 3)
    db.commit()
    return {
        "message": "盘点完成",
        "product_id": product.id,
        "stock": round(stock_row.stock, 3),
        "diff": diff,
    }


@router.post("/breakage", response_model=dict)
def breakage(
    data: InventoryBreakage,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """报损：扣减当前门店库存并写入报损流水，库存不足时拒绝。"""
    product = _get_product(db, data.product_id, tenant_id)
    stock_row = ProductStockService.get_or_create(db, product, store_id)
    if (stock_row.stock or 0) < data.qty:
        raise HTTPException(status_code=400, detail="报损数量超过当前库存")
    InventoryService.record(
        db,
        product,
        "breakage",
        -data.qty,
        store_id=store_id,
        operator_id=data.operator_id,
        tenant_id=tenant_id,
    )
    db.commit()
    return {
        "message": "报损成功",
        "product_id": product.id,
        "stock": round(stock_row.stock or 0, 3),
    }


@router.get("/movements", response_model=dict)
def list_movements(
    product_id: int | None = None,
    type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
):
    """分页查询库存变动流水（当前门店，时间倒序）。"""
    stmt = select(InventoryMovement).where(InventoryMovement.store_id == store_id)
    if product_id:
        stmt = stmt.where(InventoryMovement.product_id == product_id)
    if type:
        stmt = stmt.where(InventoryMovement.type == type)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(InventoryMovement.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [InventoryMovementOut.model_validate(r) for r in rows]
    # 填充商品名称，便于列表展示（已删除商品也保留名称，用于追溯）
    product_ids = {r.product_id for r in rows}
    names = {
        p.id: p.name
        for p in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
    }
    for out in items:
        out.product_name = names.get(out.product_id)
    return {"total": total, "page": page, "page_size": page_size, "items": items}
