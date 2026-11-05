"""操作日志 API：分页查询关键操作留痕。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.operation_log_service import OperationLogService

# 操作日志路由
router = APIRouter(prefix="/api/operation-logs", tags=["操作日志"])


@router.get("", response_model=dict)
def list_operation_logs(
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """分页查询操作日志（按操作内容/操作人搜索）。"""
    return OperationLogService.list_logs(db, keyword, page, page_size)
