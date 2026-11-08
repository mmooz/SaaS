"""商品管理 API：列表、详情、新增、更新、删除、批量改价、Excel 导入导出。"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_manager_user, get_store_id, get_tenant_id
from app.models import Product, ProductPriceHistory, User
from app.schemas.batch_price_request import BatchPriceRequest
from app.schemas.import_result import ImportResult
from app.schemas.product_create import ProductCreate
from app.schemas.product_out import ProductOut
from app.schemas.product_query import ProductQuery
from app.schemas.product_update import ProductUpdate
from app.services.excel_service import (
    MAX_IMPORT_FILE_BYTES,
    deleted_barcode,
    excel_service,
    release_deleted_barcode,
)
from app.services.inventory_service import round_amount, round_stock
from app.services.operation_log_service import OperationLogService
from app.services.product_stock_service import ProductStockService
from app.services.unit_service import UnitConfigError, build_units_list, serialize_units

# 商品路由
router = APIRouter(prefix="/api/products", tags=["商品管理"])


def fill_store_stock(
    db: Session, items: list[ProductOut], products: list[Product], store_id: int
) -> list[ProductOut]:
    """用当前门店库存覆盖商品响应中的库存字段（商品档案本身不再持有业务库存）。

    :param db: 数据库会话
    :param items: 商品响应模型列表
    :param products: 商品 ORM 列表（与 items 一一对应）
    :param store_id: 当前门店 ID
    :return: 填充后的响应模型列表
    """
    stocks = ProductStockService.get_map(db, [p.id for p in products], store_id)
    for out, product in zip(items, products):
        row = stocks.get(product.id)
        out.stock = round_stock(row.stock) if row else 0
        out.safety_stock = (row.safety_stock or 0) if row else 0
    return items


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
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """分页查询商品列表（仅当前门店，库存取当前门店，已删除商品不返回）。"""
    base = apply_filters(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.store_id == store_id,
            Product.deleted.is_(False),
        ),
        query,
    )
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    stmt = (
        base.order_by(Product.category_id, Product.id)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    products = db.scalars(stmt).all()
    items = [ProductOut.model_validate(p) for p in products]
    # 填充分类名称与多单位列表
    for out, product in zip(items, products):
        out.category_name = product.category.name if product.category else None
        out.units = build_units_list(product)
    fill_store_stock(db, items, list(products), store_id)
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
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """导出本租户全部商品（库存取当前门店）为 Excel 文件。"""
    buffer = excel_service.export_products(db, tenant_id, store_id)
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
    _user: User = Depends(get_manager_user),
):
    """批量改价：按分类/商品范围 + 比例/固定值调整，并记录价格历史。"""
    # 确定改价范围（仅当前门店商品，已删除商品不参与改价）
    stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        Product.store_id == store_id,
        Product.deleted.is_(False),
    )
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
        new_price = round_amount(max(0, new_price))
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
    _user: User = Depends(get_manager_user),
):
    """上传 Excel 批量导入/更新商品（Q23：限制上传大小，超限返回 413）。"""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=422, detail="请上传 .xlsx 格式的 Excel 文件")
    # Q23：最多读取「上限 + 1」字节即可判定超限，避免整份大文件进入内存与事务
    content = await file.read(MAX_IMPORT_FILE_BYTES + 1)
    if len(content) > MAX_IMPORT_FILE_BYTES:
        raise HTTPException(status_code=413, detail="导入文件超过系统允许的大小上限，请拆分后重试")
    try:
        result = excel_service.import_products(db, content, tenant_id, store_id)
    except ValueError as exc:
        # 服务层整文件级校验（大小防御性复核、表头等）转成明确业务错误，不暴露为 500
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """新增商品（同租户条码唯一，库存写入当前门店）。"""
    # Q18：查重只针对未删除商品；软删行条码已被改写释放，不再占位
    exists = db.scalar(
        select(Product).where(
            Product.barcode == data.barcode,
            Product.tenant_id == tenant_id,
            Product.deleted.is_(False),
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail="条码已存在")
    # Q18：兼容 B3 之前遗留的软删行（当时只打标记未改写条码），先释放占用
    release_deleted_barcode(db, tenant_id, data.barcode)
    # 库存字段不落在商品档案上，单独写入当前门店库存表；units 由多单位字段单独处理
    try:
        units_json, base_unit, base_price, base_member = serialize_units(data.units)
    except UnitConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    product = Product(
        **data.model_dump(exclude={"store_id", "stock", "safety_stock", "units"}),
        tenant_id=tenant_id,
        store_id=store_id,
        stock=0,
        safety_stock=0,
        units_json=units_json,
    )
    if base_unit is not None:
        product.unit = base_unit
        product.price = base_price
        product.member_price = base_member
    db.add(product)
    db.flush()
    ProductStockService.apply(
        db,
        product,
        store_id,
        stock=data.stock,
        safety_stock=data.safety_stock,
    )
    OperationLogService.record(
        db, "新增商品", f"新增商品 {product.name}（{product.barcode}）", tenant_id=tenant_id
    )
    db.commit()
    db.refresh(product)
    out = ProductOut.model_validate(product)
    out.units = build_units_list(product)
    fill_store_stock(db, [out], [product], store_id)
    return out


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """获取商品详情（仅当前门店，库存取当前门店，已删除商品视为不存在）。"""
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.store_id == store_id,
            Product.deleted.is_(False),
        )
    )
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    out = ProductOut.model_validate(product)
    out.units = build_units_list(product)
    fill_store_stock(db, [out], [product], store_id)
    return out


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """更新商品（仅当前门店，仅更新传入字段，已删除商品不可编辑）。"""
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.store_id == store_id,
            Product.deleted.is_(False),
        )
    )
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    # 条码唯一性校验（同租户范围内，Q18：排除已软删商品）
    if data.barcode:
        dup = db.scalar(
            select(Product).where(
                Product.barcode == data.barcode,
                Product.id != product_id,
                Product.tenant_id == tenant_id,
                Product.deleted.is_(False),
            )
        )
        if dup:
            raise HTTPException(status_code=409, detail="条码已被其他商品使用")
        # Q18：释放 B3 之前遗留软删行占用的同值条码，避免写入触发唯一键冲突
        release_deleted_barcode(db, tenant_id, data.barcode)
    # 记录价格变更历史
    old_price = product.price
    payload = data.model_dump(exclude_unset=True)
    # 库存与安全库存属于当前门店，不写回商品档案
    stock = payload.pop("stock", None)
    safety_stock = payload.pop("safety_stock", None)
    # 多单位列表整体覆盖既有配置
    units_payload = payload.pop("units", None)
    if units_payload is not None:
        try:
            units_json, base_unit, base_price, base_member = serialize_units(units_payload)
        except UnitConfigError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        product.units_json = units_json
        if base_unit is not None:
            product.unit = base_unit
            product.price = base_price
            product.member_price = base_member
    for key, value in payload.items():
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
    if stock is not None or safety_stock is not None:
        ProductStockService.apply(
            db, product, store_id, stock=stock, safety_stock=safety_stock
        )
    db.commit()
    db.refresh(product)
    out = ProductOut.model_validate(product)
    out.units = build_units_list(product)
    fill_store_stock(db, [out], [product], store_id)
    return out


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """删除商品（仅当前门店，软删除：仅打标记并停用，保留数据用于历史追溯）。"""
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.store_id == store_id,
            Product.deleted.is_(False),
        )
    )
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    # 先取出名称/条码，供操作日志使用
    name, barcode = product.name, product.barcode
    # 标记删除并停用，避免收银端继续售卖
    product.deleted = True
    product.enabled = False
    # Q18：租户内条码是物理唯一索引，软删行仍会占位导致原条码永久无法复用。
    # 改写为 D{id}（雪花 ID ≤19 位 + 1 位前缀 = 20 ≤ String(32)）释放占用，
    # 不需要 DDL / 部分唯一索引；PG baseline 改部分唯一索引后可移除该过渡逻辑。
    product.barcode = deleted_barcode(product.id)
    db.commit()
    OperationLogService.record(
        db, "删除商品", f"删除商品 {name}（{barcode}）", tenant_id=tenant_id
    )
    db.commit()
    return {"message": "删除成功"}
