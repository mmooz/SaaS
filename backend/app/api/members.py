"""会员管理 API：建档、查询、储值充值、消费扣款、积分调整与流水查询。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_manager_user, get_store_id, get_tenant_id
from app.models import Member, MemberTransaction, Order, User
from app.schemas.member_consume import MemberConsume
from app.schemas.member_create import MemberCreate
from app.schemas.member_out import MemberOut
from app.schemas.member_points_adjust import MemberPointsAdjust
from app.schemas.member_recharge import MemberRecharge
from app.schemas.member_transaction_out import MemberTransactionOut
from app.schemas.member_update import MemberUpdate
from app.services.member_tx_store_service import is_store_attribution_reliable
from app.services.operation_log_service import OperationLogService
from app.services.report_net import net_order, refund_map
from app.services.setting_service import MAX_RECHARGE_AMOUNT, SettingService

# 会员路由
router = APIRouter(prefix="/api/members", tags=["会员管理"])


def _get_member(db: Session, member_id: int, tenant_id: int) -> Member:
    """按主键取会员并校验归属当前租户，不存在则抛 404。

    :param db: 数据库会话
    :param member_id: 会员 ID
    :param tenant_id: 当前租户 ID
    :return: 会员 ORM 对象
    """
    member = db.scalar(
        select(Member).where(Member.id == member_id, Member.tenant_id == tenant_id)
    )
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    return member


@router.post("", response_model=MemberOut, status_code=201)
def create_member(
    data: MemberCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """会员建档：同租户手机号已存在则返回 409。

    需求变更登记（Q17 / 拍板 1，B3 **不改代码、门槛维持 manager 及以上**）：
    基线写「收银员可建档」，与当前 ``get_manager_user`` 门槛存在偏差，但「手机号
    建档」功能本身已实现（按 mobile + tenant_id 查重），偏差仅在角色门槛，属需求
    变更而非功能缺失。建档是资金账户创建入口，放宽到 cashier 会扩大资损面，与
    R5 / Q06 的收紧方向相反；如产品确需放宽须单独拍板并配套操作日志与 R5 校验。
    """
    # 手机号唯一性校验（限定当前租户）
    existing = db.scalar(
        select(Member).where(Member.mobile == data.mobile, Member.tenant_id == tenant_id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="该手机号已建档")

    member = Member(
        **data.model_dump(exclude={"store_id"}),
        tenant_id=tenant_id,
        store_id=store_id,
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
    tenant_id: int = Depends(get_tenant_id),
):
    """分页查询会员：可按手机号或姓名模糊搜索（租户级共享，各门店同一套会员库）。"""
    stmt = select(Member).where(Member.tenant_id == tenant_id)
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


@router.get("/stats", response_model=dict)
def member_stats(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """会员概览统计：会员总量/储值余额按租户，消费笔数与金额按当前门店。"""
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)

    # 会员总量、新增与储值余额为租户口径（会员库跨门店共享）
    total = db.scalar(
        select(func.count()).select_from(Member).where(Member.tenant_id == tenant_id)
    ) or 0
    new_today = (
        db.scalar(
            select(func.count())
            .select_from(Member)
            .where(Member.tenant_id == tenant_id, Member.created_at >= today_start)
        )
        or 0
    )
    balance_total = db.scalar(
        select(func.sum(Member.balance)).where(Member.tenant_id == tenant_id)
    ) or 0
    # 充值为储值口径，按租户统计
    recharge_month = (
        db.scalar(
            select(func.sum(MemberTransaction.amount))
            .join(Member, Member.id == MemberTransaction.member_id)
            .where(
                Member.tenant_id == tenant_id,
                MemberTransaction.type == "recharge",
                MemberTransaction.created_at >= month_start,
            )
        )
        or 0
    )

    # 消费排行前十：累计消费为会员租户口径，笔数与本月消费按当前门店
    top_members = db.scalars(
        select(Member)
        .where(Member.tenant_id == tenant_id)
        .order_by(Member.total_spent.desc())
        .limit(10)
    ).all()
    # Q05（A.6 #3 隐性波及点）：会员概览与日报 / 班次统一净额法，
    # 去掉 status == "paid" 过滤，退款后整单不再从统计中消失。
    # 退款映射按订单关联统计（口径见 services/report_net.py），本月消费累加订单净额。
    member_ids = [m.id for m in top_members]
    order_counts: dict[int, int] = {}
    month_spent: dict[int, float] = {}
    if member_ids:
        member_orders = list(
            db.scalars(
                select(Order).where(
                    Order.member_id.in_(member_ids),
                    Order.store_id == store_id,
                )
            ).all()
        )
        refunds = refund_map(db, month_start, now, store_id, orders=member_orders)
        for order in member_orders:
            order_counts[order.member_id] = order_counts.get(order.member_id, 0) + 1
            if order.created_at and order.created_at >= month_start:
                month_spent[order.member_id] = (
                    month_spent.get(order.member_id, 0.0)
                    + net_order(order, refunds)
                )

    return {
        "total": total,
        "new_today": new_today,
        "balance_total": round(balance_total, 2),
        "recharge_this_month": round(recharge_month, 2),
        "top": [
            {
                "id": m.id,
                "mobile": m.mobile,
                "name": m.name,
                "level": m.level,
                "points": m.points or 0,
                "total_spent": round(m.total_spent or 0, 2),
                "order_count": order_counts.get(m.id, 0),
                "month_spent": round(month_spent.get(m.id, 0), 2),
            }
            for m in top_members
        ],
    }


@router.get("/transactions/all", response_model=dict)
def list_all_transactions(
    member_id: int | None = None,
    type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """分页查询全部会员流水（可按会员/类型筛选），用于后台充值/积分记录（租户口径）。"""
    stmt = (
        select(MemberTransaction)
        .join(Member, Member.id == MemberTransaction.member_id)
        .where(Member.tenant_id == tenant_id)
    )
    if member_id:
        stmt = stmt.where(MemberTransaction.member_id == member_id)
    if type:
        stmt = stmt.where(MemberTransaction.type == type)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(MemberTransaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    # 补充会员手机号与姓名，便于后台列表展示
    member_ids = {r.member_id for r in rows}
    members = {
        m.id: m
        for m in db.scalars(select(Member).where(Member.id.in_(member_ids))).all()
    }
    items = []
    for row in rows:
        item = MemberTransactionOut.model_validate(row).model_dump()
        member = members.get(row.member_id)
        item["mobile"] = member.mobile if member else None
        item["member_name"] = member.name if member else None
        # Q24：流水级门店归属标注（零回填，仅依据配置基线判定历史数据）
        item["store_attribution_reliable"] = is_store_attribution_reliable(row.created_at)
        items.append(item)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/{mobile}", response_model=MemberOut)
def get_member_by_mobile(
    mobile: str,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """按手机号查询会员（租户级共享，任一门店建档的会员各店都可用）。"""
    member = db.scalar(
        select(Member).where(Member.mobile == mobile, Member.tenant_id == tenant_id)
    )
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    return member


@router.patch("/{member_id}", response_model=MemberOut)
def update_member(
    member_id: int,
    data: MemberUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    _user: User = Depends(get_manager_user),
):
    """更新会员姓名或等级（仅修改传入字段，租户级共享）。"""
    member = _get_member(db, member_id, tenant_id)
    # 逐字段按需更新，未传字段保持原值
    if data.name is not None:
        member.name = data.name
    if data.level is not None:
        member.level = data.level
    db.commit()
    db.refresh(member)
    return member


@router.post("/{member_id}/recharge", response_model=MemberOut)
def recharge_member(
    member_id: int,
    data: MemberRecharge,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    user: User = Depends(get_manager_user),
):
    """会员储值充值：增加余额并写入充值流水（流水记录发生门店）。"""
    member = _get_member(db, member_id, tenant_id)
    # Q02：单笔充值金额（含赠金）上限，防止越权大额充值造成资损
    credit = round(data.amount + data.gift_amount, 2)
    if credit > MAX_RECHARGE_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"单笔充值金额不得超过 {MAX_RECHARGE_AMOUNT:.0f} 元",
        )
    # R4 / Q02：赠送积分由服务端 system_settings 配置读取，忽略客户端传值。
    # 数值来源改为后台已有输入控件 rechargeGift（百分比，由 SettingService 换算为
    # 每元赠送积分），运营在「储值充值赠送比例」的配置即刻生效；
    # 原 rechargeBonusPointsPerYuan 无任何 UI 控件的契约断层已废弃（见 setting_service）。
    _, bonus_per_yuan = SettingService.get_member_point_config(db, tenant_id, store_id)
    bonus_points = int(data.amount * bonus_per_yuan)
    # 增加储值余额（充值金额 + 赠送金额）
    member.balance = round((member.balance or 0) + credit, 2)
    if bonus_points:
        member.points = (member.points or 0) + bonus_points
    db.add(
        MemberTransaction(
            tenant_id=tenant_id,
            store_id=store_id,
            member_id=member.id,
            type="recharge",
            amount=credit,
            points=bonus_points,
            operator_id=user.id,
        )
    )
    # Q02：充值属于资金操作，写入操作日志（复用登录/退款/改设置的写法）
    OperationLogService.record(
        db,
        "会员充值",
        f"会员 {member.mobile} 充值 {data.amount:.2f} 元、赠金 {data.gift_amount:.2f} 元、赠送积分 {bonus_points}",
        user.id,
        tenant_id=tenant_id,
    )
    db.commit()
    db.refresh(member)
    return member


@router.post("/{member_id}/consume", response_model=MemberOut)
def consume_member(
    member_id: int,
    data: MemberConsume,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    user: User = Depends(get_manager_user),
):
    """会员消费：扣减储值余额、累计消费额并奖励积分（流水记录发生门店）。"""
    member = _get_member(db, member_id, tenant_id)
    # 余额不足则拒绝扣款
    if (member.balance or 0) < data.amount:
        raise HTTPException(status_code=400, detail="储值余额不足")

    member.balance = round((member.balance or 0) - data.amount, 2)
    member.total_spent = round((member.total_spent or 0) + data.amount, 2)
    # Q02：积分换算比例由服务端 system_settings 配置读取，客户端传值一律忽略
    points_per_yuan, _ = SettingService.get_member_point_config(db, tenant_id, store_id)
    # 按消费金额换算积分（向下取整）
    earned = int(data.amount * points_per_yuan)
    member.points = (member.points or 0) + earned
    db.add(
        MemberTransaction(
            tenant_id=tenant_id,
            store_id=store_id,
            member_id=member.id,
            type="consume",
            amount=-data.amount,
            points=earned,
            operator_id=user.id,
        )
    )
    # Q02：储值消费属于资金操作，写入操作日志
    OperationLogService.record(
        db,
        "会员消费",
        f"会员 {member.mobile} 储值消费 {data.amount:.2f} 元，获得积分 {earned}",
        user.id,
        tenant_id=tenant_id,
    )
    db.commit()
    db.refresh(member)
    return member


@router.post("/{member_id}/points", response_model=MemberOut)
def adjust_points(
    member_id: int,
    data: MemberPointsAdjust,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """手工调整会员积分（正增负减，扣减后不得为负；流水记录发生门店）。"""
    member = _get_member(db, member_id, tenant_id)
    # 扣减积分不能超过当前余额
    if data.points < 0 and (member.points or 0) + data.points < 0:
        raise HTTPException(status_code=400, detail="积分余额不足")

    member.points = (member.points or 0) + data.points
    db.add(
        MemberTransaction(
            tenant_id=tenant_id,
            store_id=store_id,
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
    tenant_id: int = Depends(get_tenant_id),
):
    """分页查询会员资金/积分流水（租户级会员，返回该会员全部门店流水，时间倒序）。"""
    _get_member(db, member_id, tenant_id)
    stmt = select(MemberTransaction).where(MemberTransaction.member_id == member_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(MemberTransaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    # Q24：逐条标注门店归属是否可信（新增可选字段，不改既有字段与状态码）
    items = []
    for row in rows:
        item = MemberTransactionOut.model_validate(row).model_dump()
        item["store_attribution_reliable"] = is_store_attribution_reliable(row.created_at)
        items.append(item)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
