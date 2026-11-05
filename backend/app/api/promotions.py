"""促销管理 API：规则增删改查与收银端生效规则查询。"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Promotion
from app.schemas.promotion_create import PromotionCreate
from app.schemas.promotion_out import PromotionOut
from app.schemas.promotion_update import PromotionUpdate

# 促销路由
router = APIRouter(prefix="/api/promotions", tags=["促销管理"])


def _dump_ids(ids: list[int] | None) -> str | None:
    """把 ID 列表序列化为 JSON 字符串（None 保持为空）。

    :param ids: 商品/分类 ID 列表
    :return: JSON 字符串或 None
    """
    return None if ids is None else json.dumps(ids, ensure_ascii=False)


def _load_ids(raw: str | None) -> list[int] | None:
    """把 JSON 字符串反序列化为 ID 列表，异常时返回 None。

    :param raw: 数据库中的 JSON 字符串
    :return: ID 列表或 None
    """
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _to_out(promo: Promotion) -> PromotionOut:
    """ORM 促销对象转换为响应模型（解析 JSON 字段）。

    :param promo: 促销 ORM 对象
    :return: 响应模型
    """
    return PromotionOut(
        id=promo.id,
        type=promo.type,
        name=promo.name,
        product_ids=_load_ids(promo.product_ids),
        category_ids=_load_ids(promo.category_ids),
        params=json.loads(promo.params or "{}"),
        start_at=promo.start_at,
        end_at=promo.end_at,
        enabled=promo.enabled,
        store_id=promo.store_id,
        created_at=promo.created_at,
    )


@router.get("", response_model=list[PromotionOut])
def list_promotions(enabled: bool | None = None, db: Session = Depends(get_db)):
    """查询促销规则列表（可按启用状态筛选，新建在前）。"""
    stmt = select(Promotion)
    if enabled is not None:
        stmt = stmt.where(Promotion.enabled == enabled)
    rows = db.scalars(stmt.order_by(Promotion.id.desc())).all()
    return [_to_out(r) for r in rows]


@router.get("/active", response_model=list[PromotionOut])
def list_active_promotions(db: Session = Depends(get_db)):
    """查询当前生效的促销规则（已启用且在时间窗口内），供收银端规则引擎使用。"""
    now = datetime.now()
    stmt = select(Promotion).where(
        Promotion.enabled.is_(True),
        or_(Promotion.start_at.is_(None), Promotion.start_at <= now),
        or_(Promotion.end_at.is_(None), Promotion.end_at >= now),
    )
    rows = db.scalars(stmt.order_by(Promotion.id.desc())).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=PromotionOut, status_code=201)
def create_promotion(data: PromotionCreate, db: Session = Depends(get_db)):
    """新增促销规则。"""
    promo = Promotion(
        type=data.type,
        name=data.name,
        product_ids=_dump_ids(data.product_ids),
        category_ids=_dump_ids(data.category_ids),
        params=json.dumps(data.params, ensure_ascii=False),
        start_at=data.start_at,
        end_at=data.end_at,
        enabled=data.enabled,
        store_id=data.store_id,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return _to_out(promo)


@router.patch("/{promotion_id}", response_model=PromotionOut)
def update_promotion(
    promotion_id: int, data: PromotionUpdate, db: Session = Depends(get_db)
):
    """更新促销规则（仅修改传入字段）。"""
    promo = db.get(Promotion, promotion_id)
    if not promo:
        raise HTTPException(status_code=404, detail="促销规则不存在")

    if data.name is not None:
        promo.name = data.name
    if data.product_ids is not None:
        promo.product_ids = _dump_ids(data.product_ids)
    if data.category_ids is not None:
        promo.category_ids = _dump_ids(data.category_ids)
    if data.params is not None:
        promo.params = json.dumps(data.params, ensure_ascii=False)
    if data.start_at is not None:
        promo.start_at = data.start_at
    if data.end_at is not None:
        promo.end_at = data.end_at
    if data.enabled is not None:
        promo.enabled = data.enabled

    db.commit()
    db.refresh(promo)
    return _to_out(promo)


@router.delete("/{promotion_id}", status_code=204)
def delete_promotion(promotion_id: int, db: Session = Depends(get_db)):
    """删除促销规则。"""
    promo = db.get(Promotion, promotion_id)
    if not promo:
        raise HTTPException(status_code=404, detail="促销规则不存在")
    db.delete(promo)
    db.commit()
