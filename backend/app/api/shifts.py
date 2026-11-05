"""交接班 API：开班、查询当前班次、班次汇总与交班。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_store_id, get_tenant_id
from app.models import ShiftSession
from app.schemas.shift_close import ShiftClose
from app.schemas.shift_open import ShiftOpen
from app.schemas.shift_out import ShiftOut
from app.schemas.shift_summary_out import ShiftSummaryOut
from app.schemas.shift_sync_request import ShiftSyncRequest
from app.services.operation_log_service import OperationLogService
from app.services.shift_service import ShiftService

# 交接班路由
router = APIRouter(prefix="/api/shifts", tags=["交接班"])


def _get_shift(db: Session, shift_id: int, store_id: int) -> ShiftSession:
    """按主键取班次并校验归属当前门店，不存在则抛 404。

    :param db: 数据库会话
    :param shift_id: 班次 ID
    :param store_id: 当前门店 ID
    :return: 班次 ORM 对象
    """
    shift = db.scalar(
        select(ShiftSession).where(ShiftSession.id == shift_id, ShiftSession.store_id == store_id)
    )
    if not shift:
        raise HTTPException(status_code=404, detail="班次不存在")
    return shift


@router.post("/open", response_model=ShiftOut)
def open_shift(
    data: ShiftOpen,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """开班：已有进行中班次则直接返回该班次。"""
    shift = ShiftService.open(db, data.cashier_id, data.base_cash, tenant_id, store_id)
    OperationLogService.record(
        db, "开班", f"收银员 {data.cashier_id} 开班，底金 {data.base_cash} 元", data.cashier_id, tenant_id=tenant_id
    )
    db.commit()
    db.refresh(shift)
    return shift


@router.post("/sync", response_model=dict)
def sync_shifts(
    data: ShiftSyncRequest,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """离线收银端批量补传班次（按班次主键幂等写入）。"""
    count = ShiftService.sync(db, data.shifts, tenant_id, store_id)
    db.commit()
    return {"synced": count}


@router.get("/current", response_model=ShiftOut | None)
def current_shift(
    cashier_id: int,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
):
    """查询收银员当前进行中的班次（限定当前门店，无则返回 null）。"""
    return ShiftService.current(db, cashier_id, store_id)


@router.get("/{shift_id}/summary", response_model=ShiftSummaryOut)
def shift_summary(
    shift_id: int,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
):
    """查询班次汇总：销售、退款与各支付方式金额。"""
    shift = _get_shift(db, shift_id, store_id)
    return ShiftService.summary(db, shift)


@router.post("/{shift_id}/close", response_model=ShiftSummaryOut)
def close_shift(
    shift_id: int,
    data: ShiftClose,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
):
    """交班：落库销售汇总、交班时间与实际点钞现金。"""
    shift = _get_shift(db, shift_id, store_id)
    if shift.status == "closed":
        raise HTTPException(status_code=400, detail="该班次已交班")
    summary = ShiftService.close(db, shift, data.actual_cash)
    OperationLogService.record(
        db,
        "交班",
        f"班次 {shift_id} 交班，销售额 {summary.total_sales} 元，实际现金 {data.actual_cash or 0} 元",
        shift.cashier_id,
        tenant_id=tenant_id,
    )
    db.commit()
    db.refresh(shift)
    return summary
