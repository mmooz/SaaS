"""商品管理 API：列表、详情、新增、更新、删除、批量改价、Excel 导入导出。"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_store_id, get_tenant_id
from app.models import Product, ProductPriceHistory
from app.schemas.batch_price_request import BatchPriceRequest
from app.schemas.import_result import ImportResult
from app.schemas.product_create import ProductCreate
from app.schemas.product_out import ProductOut
from app.schemas.product_query import ProductQuery
from app.schemas.product_update import ProductUpdate
from app.services.excel_service import excel_service
from app.services.operation_log_service import OperationLogService

# 商品路由
router = APIRouter(prefix="/api/products", tags=["商品管理"])


def apply_filters(stmt, query: ProductQuery):
    """按查询参数组装商品筛选条件。"""
    if query.keyword:
        kw = f"%{query.keyword}%"
        stmt = stmt.where(
            or_(Product.name.like(kw), Product.barcode.like(kw), Product.pinyin.like(kw))
        )
    if query.category_id:
        stmt = stmt.where(Product.category_id == query.category_id)
    if query.pricing_mode:
        stmt = stmt.where(Product.pricing_mode == query.pricing_mode)
    if query.enabled is not None:
        stmt = stmt.where(Product.enabled == query.enabled)
    return stmt


@router.get("", response_model=dict)
def list_products(
    query: ProductQuery = Depends(),
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
):
    """分页查询商品列表（支持关键字/分类/计价方式筛选，已删除商品不返回）。"""
    base = apply_filters(
        select(Product).where(Product.store_id == store_id, Product.deleted.is_(False)), query
    )
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    stmt = (
        base.order_by(Product.category_id, Product.id)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    products = db.scalars(stmt).all()
    items = [ProductOut.model_validate(p) for p in products]
    # 填充分类名称
    for out, product in zip(items, products):
        out.category_name = product.category.name if product.category else None
    return {"total": total, "page": query.page, "page_size": query.page_size, "items": items}


@router.get("/import-template")
def download_import_template():
    """下载商品导入模板（含示例行）。"""
    buffer = excel_service.build_template()
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=product_import_template.xlsx"},
    )


@router.get("/export")
def export_products(
    db: Session = Depends(get_db), store_id: int = Depends(get_store_id)
):
    """导出当前门店全部商品为 Excel 文件。"""
    buffer = excel_service.export_products(db, store_id)
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=products_export.xlsx"},
    )


@router.post("/batch-price", response_model=dict)
def batch_adjust_price(
    data: BatchPriceRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """批量改价：按分类/商品范围 + 比例/固定值调整，并记录价格历史。"""
    # 确定改价范围（限定当前门店，已删除商品不参与改价）
    stmt = select(Product).where(Product.store_id == store_id, Product.deleted.is_(False))
    if data.mode == "category":
        if data.category_id is None:
            raise HTTPException(status_code=422, detail="按分类改价需提供分类 ID")
        stmt = stmt.where(Product.category_id == data.category_id)
    else:
        if not data.product_ids:
            raise HTTPException(status_code=422, detail="按商品改价需提供商品 ID 列表")
        stmt = stmt.where(Product.id.in_(data.product_ids))

    products = db.scalars(stmt).all()
    if not products:
        raise HTTPException(status_code=404, detail="未找到符合条件的商品")

    # 应用调价并记录价格历史
    for product in products:
        new_price = product.price
        if data.adjust_type == "percent":
            new_price = product.price * (1 + data.value / 100)
        else:
            new_price = product.price + data.value
        new_price = round(max(0, new_price), 2)
        if new_price != product.price:
            db.add(
                ProductPriceHistory(
                    tenant_id=tenant_id,
                    product_id=product.id,
                    old_price=product.price,
                    new_price=new_price,
                )
            )
            product.price = new_price

    db.commit()
    OperationLogService.record(
        db, "批量改价", f"调整 {len(products)} 个商品价格", tenant_id=tenant_id
    )
    db.commit()
    return {"message": f"已调整 {len(products)} 个商品的价格"}


@router.post("/import", response_model=ImportResult)
async def import_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """上传 Excel 批量导入/更新商品。"""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=422, detail="请上传 .xlsx 格式的 Excel 文件")
    content = await file.read()
    result = excel_service.import_products(db, content, tenant_id, store_id)
    return result


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """新增商品（同租户条码唯一）。"""
    exists = db.scalar(
        select(Product).where(
            Product.barcode == data.barcode, Product.tenant_id == tenant_id
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail="条码已存在")
    product = Product(
        **data.model_dump(exclude={"store_id"}),
        tenant_id=tenant_id,
        store_id=store_id,
    )
    db.add(product)
    db.flush()
    OperationLogService.record(
        db, "新增商品", f"新增商品 {product.name}（{product.barcode}）", tenant_id=tenant_id
    )
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
):
    """获取商品详情（已删除商品视为不存在）。"""
    product = db.scalar(
        select(Product).where(
            Product.id == product_id, Product.store_id == store_id, Product.deleted.is_(False)
        )
    )
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """更新商品（仅更新传入字段，已删除商品不可编辑）。"""
    product = db.scalar(
        select(Product).where(
            Product.id == product_id, Product.store_id == store_id, Product.deleted.is_(False)
        )
    )
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    # 条码唯一性校验（同租户范围内）
    if data.barcode:
        dup = db.scalar(
            select(Product).where(
                Product.barcode == data.barcode,
                Product.id != product_id,
                Product.tenant_id == tenant_id,
            )
        )
        if dup:
            raise HTTPException(status_code=409, detail="条码已被其他商品使用")
    # 记录价格变更历史
    old_price = product.price
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    if product.price != old_price:
        db.add(
            ProductPriceHistory(
                tenant_id=tenant_id,
                product_id=product.id,
                old_price=old_price,
                new_price=product.price,
            )
        )
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """删除商品（软删除：仅打标记并停用，保留数据用于历史追溯）。"""
    product = db.scalar(
        select(Product).where(
            Product.id == product_id, Product.store_id == store_id, Product.deleted.is_(False)
        )
    )
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    # 先取出名称/条码，供操作日志使用
    name, barcode = product.name, product.barcode
    # 标记删除并停用，避免收银端继续售卖
    product.deleted = True
    product.enabled = False
    db.commit()
    OperationLogService.record(
        db, "删除商品", f"删除商品 {name}（{barcode}）", tenant_id=tenant_id
    )
    db.commit()
    return {"message": "删除成功"}
