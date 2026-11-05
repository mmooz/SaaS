"""交接班 API：开班、查询当前班次、班次汇总与交班。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ShiftSession
from app.schemas.shift_close import ShiftClose
from app.schemas.shift_open import ShiftOpen
from app.schemas.shift_out import ShiftOut
from app.schemas.shift_summary_out import ShiftSummaryOut
from app.services.operation_log_service import OperationLogService
from app.services.shift_service import ShiftService

# 交接班路由
router = APIRouter(prefix="/api/shifts", tags=["交接班"])


@router.post("/open", response_model=ShiftOut)
def open_shift(data: ShiftOpen, db: Session = Depends(get_db)):
    """开班：已有进行中班次则直接返回该班次。"""
    shift = ShiftService.open(db, data.cashier_id, data.base_cash)
    OperationLogService.record(
        db, "开班", f"收银员 {data.cashier_id} 开班，底金 {data.base_cash} 元", data.cashier_id
    )
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/current", response_model=ShiftOut | None)
def current_shift(cashier_id: int, db: Session = Depends(get_db)):
    """查询收银员当前进行中的班次（无则返回 null）。"""
    return ShiftService.current(db, cashier_id)


@router.get("/{shift_id}/summary", response_model=ShiftSummaryOut)
def shift_summary(shift_id: int, db: Session = Depends(get_db)):
    """查询班次汇总：销售、退款与各支付方式金额。"""
    shift = db.get(ShiftSession, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="班次不存在")
    return ShiftService.summary(db, shift)


@router.post("/{shift_id}/close", response_model=ShiftSummaryOut)
def close_shift(shift_id: int, data: ShiftClose, db: Session = Depends(get_db)):
    """交班：落库销售汇总、交班时间与实际点钞现金。"""
    shift = db.get(ShiftSession, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="班次不存在")
    if shift.status == "closed":
        raise HTTPException(status_code=400, detail="该班次已交班")
    summary = ShiftService.close(db, shift, data.actual_cash)
    OperationLogService.record(
        db,
        "交班",
        f"班次 {shift_id} 交班，销售额 {summary.total_sales} 元，实际现金 {data.actual_cash or 0} 元",
        shift.cashier_id,
    )
    db.commit()
    db.refresh(shift)
    return summary
