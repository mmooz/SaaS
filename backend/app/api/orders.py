"""订单管理 API：收银端订单上传（幂等）与订单查询。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, OrderItem
from app.schemas.order_create import OrderCreate
from app.schemas.order_out import OrderOut

# 订单路由
router = APIRouter(prefix="/api/orders", tags=["订单管理"])


@router.post("", response_model=OrderOut, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """收银端上传订单：按 order_no 幂等去重，重复上传返回已存在的订单。"""
    # 幂等检查：订单号已存在则直接返回（收银端离线重传场景）
    existing = db.scalar(select(Order).where(Order.order_no == data.order_no))
    if existing:
        return existing

    # 创建订单主记录
    order = Order(
        order_no=data.order_no,
        store_id=data.store_id,
        cashier_id=data.cashier_id,
        shift_id=data.shift_id,
        status=data.status,
        total_amount=data.total_amount,
        discount_amount=data.discount_amount,
        pay_details=data.pay_details,
        member_id=data.member_id,
        remark=data.remark,
        synced=True,
    )
    # 创建订单明细
    for item in data.items:
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                name=item.name,
                qty=item.qty,
                weight_kg=item.weight_kg,
                unit_price=item.unit_price,
                amount=item.amount,
                is_weighted=item.is_weighted,
                label_printed=item.label_printed,
            )
        )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=dict)
def list_orders(
    start: datetime | None = None,
    end: datetime | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """分页查询订单（支持按时间范围与状态筛选）。"""
    stmt = select(Order)
    if start:
        stmt = stmt.where(Order.created_at >= start)
    if end:
        stmt = stmt.where(Order.created_at <= end)
    if status:
        stmt = stmt.where(Order.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    orders = db.scalars(
        stmt.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [OrderOut.model_validate(o) for o in orders]
    # 填充明细（selectin 预加载避免 N+1 查询）
    for out, order in zip(items, orders):
        out.items = [item for item in order.items]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{order_no}", response_model=OrderOut)
def get_order(order_no: str, db: Session = Depends(get_db)):
    """按订单号查询订单详情。"""
    order = db.scalar(select(Order).where(Order.order_no == order_no))
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    out = OrderOut.model_validate(order)
    out.items = [item for item in order.items]
    return out
