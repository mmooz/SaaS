"""收银端数据同步 API：商品/分类/促销/会员增量下发与删除标记。

Q07：``server_time`` 统一为 naive UTC（``datetime.utcnow()``），与 SQLite
``func.now()`` 生成的 UTC 时间对齐；``after`` 若为带时区的 ISO 串（含 Z）先转
naive UTC，避免本地 UTC+8 与 UTC 混用导致增量永久拉不到。

Q19：载荷补齐 ``deleted_ids`` / ``disabled_ids`` tombstone、生效促销全量、
租户级会员增量与启用分类；促销保持门店级（待拍板项 7 未定），会员按
tenant_id 过滤且不含余额/积分/口令等敏感字段。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.promotions import _to_out as _promotion_to_out
from app.database import get_db
from app.dependencies import get_store_id, get_tenant_id
from app.models import Category, Member, Product, Promotion
from app.schemas.category_out import CategoryOut
from app.schemas.member_sync_out import MemberSyncOut
from app.schemas.product_out import ProductOut
from app.services.product_stock_service import ProductStockService

# 同步路由
router = APIRouter(prefix="/api/sync", tags=["数据同步"])


def _naive_utc(value: datetime | None) -> datetime | None:
    """把同步游标统一成 naive UTC，与库中 ``func.now()`` 的时间口径一致。

    :param value: FastAPI 解析后的 after 参数（可能带时区，也可能为 naive）
    :return: naive UTC 时间；None 表示首次全量同步
    """
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    # 新版本 server_time 已是 naive UTC，旧客户端传来的 naive 值同样按 UTC 处理
    return value


@router.get("/products", response_model=dict)
def sync_products(
    after: datetime | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """增量拉取商品/分类/促销/会员，并下发软删与停用商品的 tombstone。

    商品与分类为租户级共享，库存取当前门店；促销为门店级生效规则全量下发；
    会员为租户级共享增量。首次同步不传 after，返回全量数据。

    :param after: 上次同步返回的 server_time（naive UTC 或带时区的 ISO 串）
    :param db: 数据库会话
    :param tenant_id: 由令牌上下文解析出的租户 ID
    :param store_id: 由 X-Store-Id 解析出的门店 ID
    :return: 同步载荷字典
    """
    cursor = _naive_utc(after)

    # 1. 商品增量：只下发未删除且启用的商品；停用/删除走下面的 tombstone
    product_stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        Product.deleted.is_(False),
        Product.enabled.is_(True),
    )
    if cursor:
        product_stmt = product_stmt.where(Product.updated_at > cursor)
    products = db.scalars(product_stmt.order_by(Product.id)).all()
    product_list = [ProductOut.model_validate(p) for p in products]
    stocks = ProductStockService.get_map(db, [p.id for p in products], store_id)
    for out, product in zip(product_list, products):
        out.category_name = product.category.name if product.category else None
        # 库存按当前门店下发（语义保持不变）
        row = stocks.get(product.id)
        out.stock = round(row.stock or 0, 3) if row else 0
        out.safety_stock = (row.safety_stock or 0) if row else 0

    # 2. 软删 tombstone：删除动作同样按 after 过滤，首次全量时下发全部已删 ID
    deleted_stmt = select(Product.id).where(
        Product.tenant_id == tenant_id, Product.deleted.is_(True)
    )
    if cursor:
        deleted_stmt = deleted_stmt.where(Product.updated_at > cursor)
    deleted_ids = [str(pid) for pid in db.scalars(deleted_stmt).all()]

    # 3. 停用 tombstone：与软删互斥，避免同一商品出现在两个列表里
    disabled_stmt = select(Product.id).where(
        Product.tenant_id == tenant_id,
        Product.deleted.is_(False),
        Product.enabled.is_(False),
    )
    if cursor:
        disabled_stmt = disabled_stmt.where(Product.updated_at > cursor)
    disabled_ids = [str(pid) for pid in db.scalars(disabled_stmt).all()]

    # 4. 分类：全量下发但只保留启用分类（字段与 CategoryOut 保持一致）
    categories = db.scalars(
        select(Category)
        .where(Category.tenant_id == tenant_id, Category.enabled.is_(True))
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

    # 5. 促销：模型只有 created_at 没有 updated_at，因此按当前门店 + 时间窗 +
    #    enabled 全量下发生效规则，与 /api/promotions/active 口径一致（本地时间）。
    #    促销保持门店级，不擅自提升为租户级（待拍板项 7 未定）。
    now = datetime.now()
    promo_rows = db.scalars(
        select(Promotion)
        .where(
            Promotion.tenant_id == tenant_id,
            Promotion.store_id == store_id,
            Promotion.enabled.is_(True),
            or_(Promotion.start_at.is_(None), Promotion.start_at <= now),
            or_(Promotion.end_at.is_(None), Promotion.end_at >= now),
        )
        .order_by(Promotion.id.desc())
    ).all()
    promotions = [_promotion_to_out(p) for p in promo_rows]

    # 6. 会员：租户级共享，按 updated_at 增量；输出模型不含余额/积分/口令
    member_stmt = select(Member).where(Member.tenant_id == tenant_id)
    if cursor:
        member_stmt = member_stmt.where(Member.updated_at > cursor)
    members = [
        MemberSyncOut.model_validate(m)
        for m in db.scalars(member_stmt.order_by(Member.id)).all()
    ]

    return {
        "products": product_list,
        "categories": category_list,
        "deleted_ids": deleted_ids,
        "disabled_ids": disabled_ids,
        "promotions": promotions,
        "members": members,
        # Q07：naive UTC，与 SQLite func.now() 对齐，不再用本地时间 datetime.now()
        "server_time": datetime.utcnow().isoformat(),
    }
