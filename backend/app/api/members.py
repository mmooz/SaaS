"""会员管理 API：建档、查询、储值充值、消费扣款、积分调整与流水查询。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Member, MemberTransaction
from app.schemas.member_consume import MemberConsume
from app.schemas.member_create import MemberCreate
from app.schemas.member_out import MemberOut
from app.schemas.member_points_adjust import MemberPointsAdjust
from app.schemas.member_recharge import MemberRecharge
from app.schemas.member_transaction_out import MemberTransactionOut
from app.schemas.member_update import MemberUpdate

# 会员路由
router = APIRouter(prefix="/api/members", tags=["会员管理"])


def _get_member(db: Session, member_id: int) -> Member:
    """按主键取会员，不存在则抛 404。

    :param db: 数据库会话
    :param member_id: 会员 ID
    :return: 会员 ORM 对象
    """
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    return member


@router.post("", response_model=MemberOut, status_code=201)
def create_member(data: MemberCreate, db: Session = Depends(get_db)):
    """会员建档：手机号已存在则返回 409。"""
    # 手机号唯一性校验
    existing = db.scalar(select(Member).where(Member.mobile == data.mobile))
    if existing:
        raise HTTPException(status_code=409, detail="该手机号已建档")

    member = Member(
        mobile=data.mobile,
        name=data.name,
        level=data.level,
        store_id=data.store_id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("", response_model=dict)
def list_members(
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """分页查询会员：可按手机号或姓名模糊搜索。"""
    stmt = select(Member)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Member.mobile.like(like), Member.name.like(like)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    members = db.scalars(
        stmt.order_by(Member.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [MemberOut.model_validate(m) for m in members],
    }


@router.get("/{mobile}", response_model=MemberOut)
def get_member_by_mobile(mobile: str, db: Session = Depends(get_db)):
    """按手机号查询会员（收银端扫会员码/输手机号识别）。"""
    member = db.scalar(select(Member).where(Member.mobile == mobile))
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    return member


@router.patch("/{member_id}", response_model=MemberOut)
def update_member(member_id: int, data: MemberUpdate, db: Session = Depends(get_db)):
    """更新会员姓名或等级（仅修改传入字段）。"""
    member = _get_member(db, member_id)
    # 逐字段按需更新，未传字段保持原值
    if data.name is not None:
        member.name = data.name
    if data.level is not None:
        member.level = data.level
    db.commit()
    db.refresh(member)
    return member


@router.post("/{member_id}/recharge", response_model=MemberOut)
def recharge_member(member_id: int, data: MemberRecharge, db: Session = Depends(get_db)):
    """会员储值充值：增加余额并写入充值流水。"""
    member = _get_member(db, member_id)
    # 增加储值余额
    member.balance = round((member.balance or 0) + data.amount, 2)
    # 活动赠送积分（如有）
    if data.bonus_points:
        member.points = (member.points or 0) + data.bonus_points
    db.add(
        MemberTransaction(
            member_id=member.id,
            type="recharge",
            amount=data.amount,
            points=data.bonus_points,
            operator_id=data.operator_id,
        )
    )
    db.commit()
    db.refresh(member)
    return member


@router.post("/{member_id}/consume", response_model=MemberOut)
def consume_member(member_id: int, data: MemberConsume, db: Session = Depends(get_db)):
    """会员消费：扣减储值余额、累计消费额并奖励积分。"""
    member = _get_member(db, member_id)
    # 余额不足则拒绝扣款
    if (member.balance or 0) < data.amount:
        raise HTTPException(status_code=400, detail="储值余额不足")

    member.balance = round((member.balance or 0) - data.amount, 2)
    member.total_spent = round((member.total_spent or 0) + data.amount, 2)
    # 按消费金额换算积分（向下取整）
    earned = int(data.amount * data.points_per_yuan)
    member.points = (member.points or 0) + earned
    db.add(
        MemberTransaction(
            member_id=member.id,
            type="consume",
            amount=-data.amount,
            points=earned,
            operator_id=data.operator_id,
        )
    )
    db.commit()
    db.refresh(member)
    return member


@router.post("/{member_id}/points", response_model=MemberOut)
def adjust_points(member_id: int, data: MemberPointsAdjust, db: Session = Depends(get_db)):
    """手工调整会员积分（正增负减，扣减后不得为负）。"""
    member = _get_member(db, member_id)
    # 扣减积分不能超过当前余额
    if data.points < 0 and (member.points or 0) + data.points < 0:
        raise HTTPException(status_code=400, detail="积分余额不足")

    member.points = (member.points or 0) + data.points
    db.add(
        MemberTransaction(
            member_id=member.id,
            type="points",
            amount=0,
            points=data.points,
            operator_id=data.operator_id,
        )
    )
    db.commit()
    db.refresh(member)
    return member


@router.get("/{member_id}/transactions", response_model=dict)
def list_transactions(
    member_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """分页查询会员资金/积分流水（时间倒序）。"""
    _get_member(db, member_id)
    stmt = select(MemberTransaction).where(MemberTransaction.member_id == member_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(MemberTransaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [MemberTransactionOut.model_validate(r) for r in rows],
    }
