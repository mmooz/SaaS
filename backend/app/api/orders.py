"""订单管理 API：订单上传（幂等）、查询与退款退货。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_manager_user, get_store_id, get_tenant_id
from app.models import Member, Order, OrderItem, RefundItem, RefundRecord, User
from app.schemas.order_create import OrderCreate
from app.schemas.order_out import OrderOut
from app.schemas.refund_create import RefundCreate
from app.schemas.refund_out import RefundOut
from app.services.inventory_service import InventoryService
from app.services.operation_log_service import OperationLogService
from app.services.refund_service import RefundService

# 订单路由
router = APIRouter(prefix="/api/orders", tags=["订单管理"])


def _member_mobiles(db: Session, orders: list[Order]) -> dict[int, str]:
    """批量查询订单关联会员的手机号。

    :param db: 数据库会话
    :param orders: 订单列表
    :return: 会员 ID -> 手机号
    """
    ids = {o.member_id for o in orders if o.member_id}
    if not ids:
        return {}
    rows = db.scalars(select(Member).where(Member.id.in_(ids))).all()
    return {m.id: m.mobile for m in rows}


def _refund_totals(db: Session, orders: list[Order]) -> dict[int, float]:
    """批量统计订单已退款金额。

    :param db: 数据库会话
    :param orders: 订单列表
    :return: 订单 ID -> 已退款金额
    """
    ids = [o.id for o in orders]
    if not ids:
        return {}
    rows = db.execute(
        select(RefundRecord.order_id, func.sum(RefundRecord.amount))
        .where(RefundRecord.order_id.in_(ids))
        .group_by(RefundRecord.order_id)
    ).all()
    return {order_id: round(float(total or 0), 2) for order_id, total in rows}


def _refunded_item_map(db: Session, orders: list[Order]) -> dict[int, set[int]]:
    """批量查询各订单已退货的明细主键。

    :param db: 数据库会话
    :param orders: 订单列表
    :return: 订单 ID -> 已退货明细主键集合
    """
    ids = [o.id for o in orders]
    if not ids:
        return {}
    rows = db.execute(
        select(RefundRecord.order_id, RefundItem.order_item_id)
        .join(RefundItem, RefundItem.refund_id == RefundRecord.id)
        .where(RefundRecord.order_id.in_(ids))
    ).all()
    result: dict[int, set[int]] = {}
    for order_id, item_id in rows:
        if item_id is not None:
            result.setdefault(order_id, set()).add(item_id)
    return result


def _serialize(
    db: Session, orders: list[Order], with_mobile: bool = True
) -> list[OrderOut]:
    """把订单 ORM 批量转换为响应模型（补齐会员手机号、退款信息）。

    :param db: 数据库会话
    :param orders: 订单列表
    :param with_mobile: 是否填充会员手机号
    :return: 订单响应模型列表
    """
    mobiles = _member_mobiles(db, orders) if with_mobile else {}
    totals = _refund_totals(db, orders)
    refunded_map = _refunded_item_map(db, orders)
    result: list[OrderOut] = []
    for order in orders:
        out = OrderOut.model_validate(order)
        out.member_mobile = mobiles.get(order.member_id) if order.member_id else None
        out.refunded_amount = totals.get(order.id, 0)
        # 标记已退货明细，收银端据此禁用重复退货（输出 ID 为字符串，需统一类型比较）
        refunded_ids = {str(item_id) for item_id in refunded_map.get(order.id, set())}
        for item in out.items:
            item.refunded = item.id in refunded_ids
        result.append(out)
    return result


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """收银端上传订单：按 order_no 幂等去重，重复上传返回已存在的订单。"""
    # Q03 幂等检查：order_no 有全局唯一约束，必须先按单号全局查一次。
    # 命中但租户/门店上下文不同 -> 409 冲突（既不能把他人订单当幂等结果返回，
    # 也不能走到新建分支撞唯一索引报 500）；上下文相同 -> 幂等返回原单。
    existing = db.scalar(select(Order).where(Order.order_no == data.order_no))
    if existing:
        if existing.tenant_id != tenant_id or existing.store_id != store_id:
            raise HTTPException(
                status_code=409,
                detail="订单号已被其它门店或租户使用，请更换单号后重试",
            )
        return _serialize(db, [existing])[0]

    # 创建订单主记录（离线补传时沿用收银端生成的 ID 与下单时间；租户/门店以当前上下文为准）
    order_kwargs = {
        "order_no": data.order_no,
        "tenant_id": tenant_id,
        "store_id": store_id,
        "cashier_id": data.cashier_id,
        "shift_id": data.shift_id,
        "status": data.status,
        "total_amount": data.total_amount,
        "discount_amount": data.discount_amount,
        "pay_details": data.pay_details,
        "member_id": data.member_id,
        "remark": data.remark,
        "synced": True,
    }
    if data.id is not None:
        order_kwargs["id"] = data.id
    if data.created_at is not None:
        order_kwargs["created_at"] = data.created_at
    order = Order(**order_kwargs)
    # 创建订单明细（同样保留离线端生成的明细 ID 与时间；明细继承租户 ID）
    for item in data.items:
        item_kwargs = {
            "tenant_id": tenant_id,
            "product_id": item.product_id,
            "name": item.name,
            "qty": item.qty,
            "weight_kg": item.weight_kg,
            "unit_price": item.unit_price,
            "amount": item.amount,
            "is_weighted": item.is_weighted,
            "label_printed": item.label_printed,
        }
        if item.id is not None:
            item_kwargs["id"] = item.id
        if item.created_at is not None:
            item_kwargs["created_at"] = item.created_at
        order.items.append(OrderItem(**item_kwargs))
    db.add(order)
    # 先落库主表以获取订单 ID，再由库存服务按明细扣减库存
    db.flush()
    InventoryService.deduct_for_order(db, order)
    db.commit()
    db.refresh(order)
    return _serialize(db, [order])[0]


@router.get("", response_model=dict)
def list_orders(
    keyword: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
):
    """分页查询订单（支持按订单号/会员手机号、时间范围与状态筛选）。"""
    stmt = select(Order).where(Order.store_id == store_id)
    if keyword:
        # 关键字同时匹配订单号与会员手机号（退款页搜索用）
        like = f"%{keyword.strip()}%"
        stmt = stmt.outerjoin(Member, Order.member_id == Member.id).where(
            or_(Order.order_no.ilike(like), Member.mobile.ilike(like))
        )
    if start:
        stmt = stmt.where(Order.created_at >= start)
    if end:
        stmt = stmt.where(Order.created_at <= end)
    if status:
        stmt = stmt.where(Order.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    orders = list(
        db.scalars(
            stmt.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": _serialize(db, orders),
    }


@router.get("/{order_no}", response_model=OrderOut)
def get_order(
    order_no: str,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
):
    """按订单号查询订单详情（含退款标记）。"""
    order = db.scalar(
        select(Order).where(Order.order_no == order_no, Order.store_id == store_id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return _serialize(db, [order])[0]


@router.post("/{order_no}/refund", response_model=RefundOut, status_code=201)
def refund_order(
    order_no: str,
    data: RefundCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """订单退款/退货：整单退款或按明细退货，自动回滚库存与储值余额。"""
    # Q03：补 tenant_id 过滤，确保原订单确属当前租户+门店上下文
    order = db.scalar(
        select(Order).where(
            Order.order_no == order_no,
            Order.tenant_id == tenant_id,
            Order.store_id == store_id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    # Q03 幂等检查：refund_no 同样有全局唯一约束，先按单号全局查一次。
    # 命中但租户/原订单上下文不同 -> 409 冲突（防串单、防撞唯一索引 500）；
    # 上下文相同 -> 幂等返回原退款单。
    if data.refund_no:
        existing = db.scalar(
            select(RefundRecord).where(RefundRecord.refund_no == data.refund_no)
        )
        if existing:
            if existing.tenant_id != tenant_id or existing.order_id != order.id:
                raise HTTPException(
                    status_code=409,
                    detail="退款单号已被其它订单或租户使用，请更换单号后重试",
                )
            return existing
    try:
        record = RefundService.refund(db, order, data, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # 记录退款操作日志
    OperationLogService.record(
        db,
        "退款",
        f"订单 {order_no} 退款 {record.amount} 元（{'整单' if data.refund_type == 'full' else '单项'}）",
        data.cashier_id or order.cashier_id,
        tenant_id=tenant_id,
    )
    db.commit()
    db.refresh(record)
    return record


@router.get("/{order_no}/refunds", response_model=list[RefundOut])
def list_order_refunds(
    order_no: str,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
):
    """查询订单的全部退款记录（时间倒序）。"""
    order = db.scalar(
        select(Order).where(Order.order_no == order_no, Order.store_id == store_id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return RefundService.list_refunds(db, order.id)
