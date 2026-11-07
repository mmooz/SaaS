"""收银端数据同步 API：商品/分类/促销/会员增量下发与删除标记。

Q07：``server_time`` 统一为 naive UTC（``datetime.utcnow()``），与 SQLite
``func.now()`` 生成的 UTC 时间对齐；``after`` 若为带时区的 ISO 串（含 Z）先转
naive UTC，避免本地 UTC+8 与 UTC 混用导致增量永久拉不到。

R14：SQLite ``func.now()`` 只有秒精度，而 ``isoformat()`` 默认带微秒，
``updated_at > 带微秒的游标`` 会让「与同步发生在同一秒内的写操作」永久漏同步。
因此游标与 server_time 都截断到秒，四处增量比较统一改为 ``>=``；同秒变更会在
下次同步重复下发一次，前端按 id upsert 幂等、无害，游标前进后自动收敛。

补充（SQLAlchemy 绑定细节）：SQLite 的 ``DateTime`` 绑定格式为
``YYYY-MM-DD HH:MM:SS.ffffff``，即便微秒为 0 也会带 ``.000000``；
而 ``func.now()`` 落库的是无微秒字符串，直接比较秒级游标仍会被判为「小于」。
故比较下界额外回退 1 微秒，使同秒写入稳定命中且不误拉上一秒数据
（PostgreSQL 的 timestamp 比较同样成立）。

Q19：载荷补齐 ``deleted_ids`` / ``disabled_ids`` tombstone、生效促销全量、
租户级会员增量与启用分类；促销保持门店级（待拍板项 7 未定），会员按
tenant_id 过滤且不含余额/积分/口令等敏感字段。
"""

from datetime import datetime, timedelta, timezone

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
    """把同步游标统一成 naive UTC 且截断到秒（R14）。

    SQLite ``func.now()`` 生成的 ``updated_at`` 只有秒精度，旧客户端可能传来
    带微秒或带 Z 的 ISO 串；若不截断，同秒写入会小于游标而被严格 ``>`` 永久漏掉。

    :param value: FastAPI 解析后的 after 参数（可能带时区/微秒，也可能为 naive）
    :return: naive UTC、微秒为 0 的时间；None 表示首次全量同步
    """
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)
    # 新版本 server_time 已是 naive UTC，旧客户端传来的 naive 值同样按 UTC 处理
    return value.replace(microsecond=0)


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
    # R14：游标与 server_time 均为秒精度，与 SQLite func.now() 对齐。
    # 四处增量统一用 >= ：同步时刻同秒的变更会在下一次同步重复下发一次，
    # 前端按 id upsert 幂等、无害；游标前进到下一秒后自动收敛。
    cursor = _naive_utc(after)
    if cursor is not None:
        # SQLite DateTime 绑定恒带 .000000，而 func.now() 落库值无微秒，
        # 秒级游标直接比较仍会让同秒写入落空；比较下界回退 1 微秒精确命中，
        # 且不会误拉上一秒（游标前进后同样自动收敛）。
        try:
            cursor = cursor - timedelta(microseconds=1)
        except OverflowError:
            # 极早游标（datetime.min）已无法再回退，保持原值不影响正确性
            pass

    # 1. 商品增量：只下发未删除且启用的商品；停用/删除走下面的 tombstone
    product_stmt = select(Product).where(
        Product.tenant_id == tenant_id,
        Product.deleted.is_(False),
        Product.enabled.is_(True),
    )
    if cursor:
        product_stmt = product_stmt.where(Product.updated_at >= cursor)
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
        deleted_stmt = deleted_stmt.where(Product.updated_at >= cursor)
    deleted_ids = [str(pid) for pid in db.scalars(deleted_stmt).all()]

    # 3. 停用 tombstone：与软删互斥，避免同一商品出现在两个列表里
    disabled_stmt = select(Product.id).where(
        Product.tenant_id == tenant_id,
        Product.deleted.is_(False),
        Product.enabled.is_(False),
    )
    if cursor:
        disabled_stmt = disabled_stmt.where(Product.updated_at >= cursor)
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
        member_stmt = member_stmt.where(Member.updated_at >= cursor)
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
        # Q07/R14：naive UTC 且截断到秒，与 SQLite func.now() 的秒精度对齐
        "server_time": datetime.utcnow().replace(microsecond=0).isoformat(),
    }
