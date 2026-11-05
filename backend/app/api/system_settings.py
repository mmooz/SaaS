"""系统设置 API：按分组读写门店信息与收银参数。"""

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.operation_log_service import OperationLogService
from app.services.setting_service import SETTING_GROUPS, SettingService

# 系统设置路由
router = APIRouter(prefix="/api/settings", tags=["系统设置"])


@router.get("", response_model=dict)
def get_settings(db: Session = Depends(get_db)):
    """读取全部分组设置（store / cashier）。"""
    return SettingService.get_all(db)


@router.put("/{group}", response_model=dict)
def save_settings(
    group: str, data: dict = Body(...), db: Session = Depends(get_db)
):
    """保存指定分组的设置内容（整体覆盖）。"""
    if group not in SETTING_GROUPS:
        raise HTTPException(status_code=422, detail="不支持的设置分组")
    result = SettingService.save_group(db, group, data)
    OperationLogService.record(db, "修改设置", f"更新{group}分组设置")
    db.commit()
    return result
