"""库存管理 API：库存查询/预警、入库、盘点、报损与变动流水。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InventoryMovement, Product
from app.schemas.inventory_breakage import InventoryBreakage
from app.schemas.inventory_inbound import InventoryInbound
from app.schemas.inventory_movement_out import InventoryMovementOut
from app.schemas.inventory_stocktake import InventoryStocktake
from app.services.inventory_service import InventoryService

# 库存路由
router = APIRouter(prefix="/api/inventory", tags=["库存管理"])


def _get_product(db: Session, product_id: int) -> Product:
    """按主键取商品，不存在则抛 404。

    :param db: 数据库会话
    :param product_id: 商品 ID
    :return: 商品 ORM 对象
    """
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


def _item(product: Product) -> dict:
    """把商品转为库存列表项。

    :param product: 商品 ORM 对象
    :return: 库存展示字典
    """
    return {
        "product_id": product.id,
        "barcode": product.barcode,
        "name": product.name,
        "category": product.category.name if product.category else None,
        "unit": product.unit,
        "pricing_mode": product.pricing_mode,
        "stock": round(product.stock or 0, 3),
        "safety_stock": product.safety_stock or 0,
        "cost_price": product.cost_price,
        "status": InventoryService.status(product),
        "updated_at": product.updated_at,
    }


@router.get("", response_model=dict)
def list_inventory(
    keyword: str | None = None,
    category_id: int | None = None,
    low_only: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """分页查询库存：支持关键字/分类筛选，low_only 仅看预警商品。"""
    stmt = select(Product)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Product.name.like(like), Product.barcode.like(like)))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if low_only:
        stmt = stmt.where(
            or_(Product.stock <= 0, (Product.safety_stock > 0) & (Product.stock < Product.safety_stock))
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(Product.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_item(p) for p in rows],
    }


@router.get("/alerts", response_model=dict)
def list_alerts(db: Session = Depends(get_db)):
    """库存预警：返回已售罄或低于安全库存的商品清单。"""
    rows = db.scalars(
        select(Product)
        .where(
            or_(Product.stock <= 0, (Product.safety_stock > 0) & (Product.stock < Product.safety_stock))
        )
        .order_by(Product.stock)
    ).all()
    return {"total": len(rows), "items": [_item(p) for p in rows]}


@router.post("/inbound", response_model=dict)
def inbound(data: InventoryInbound, db: Session = Depends(get_db)):
    """采购入库：增加库存、可选更新进价并写入入库流水。"""
    product = _get_product(db, data.product_id)
    # 传入进价时同步更新商品进价
    if data.cost_price is not None:
        product.cost_price = data.cost_price
    InventoryService.record(db, product, "inbound", data.qty, operator_id=data.operator_id)
    db.commit()
    db.refresh(product)
    return {"message": "入库成功", "product_id": product.id, "stock": round(product.stock or 0, 3)}


@router.post("/stocktake", response_model=dict)
def stocktake(data: InventoryStocktake, db: Session = Depends(get_db)):
    """盘点：以实盘数覆盖库存并记录差异流水。"""
    product = _get_product(db, data.product_id)
    current = product.stock or 0
    diff = round(data.actual - current, 3)
    # 差异为零也记录盘点流水，便于追溯
    InventoryService.record(
        db, product, "stocktake", diff, operator_id=data.operator_id, apply_stock=False
    )
    product.stock = round(data.actual, 3)
    db.commit()
    db.refresh(product)
    return {"message": "盘点完成", "product_id": product.id, "stock": round(product.stock, 3), "diff": diff}


@router.post("/breakage", response_model=dict)
def breakage(data: InventoryBreakage, db: Session = Depends(get_db)):
    """报损：扣减库存并写入报损流水，库存不足时拒绝。"""
    product = _get_product(db, data.product_id)
    if (product.stock or 0) < data.qty:
        raise HTTPException(status_code=400, detail="报损数量超过当前库存")
    InventoryService.record(db, product, "breakage", -data.qty, operator_id=data.operator_id)
    db.commit()
    db.refresh(product)
    return {"message": "报损成功", "product_id": product.id, "stock": round(product.stock or 0, 3)}


@router.get("/movements", response_model=dict)
def list_movements(
    product_id: int | None = None,
    type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """分页查询库存变动流水（时间倒序）。"""
    stmt = select(InventoryMovement)
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
    # 填充商品名称，便于列表展示
    product_ids = {r.product_id for r in rows}
    names = {
        p.id: p.name
        for p in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
    }
    for out in items:
        out.product_name = names.get(out.product_id)
    return {"total": total, "page": page, "page_size": page_size, "items": items}
