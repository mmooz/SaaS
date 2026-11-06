"""数据备份 API：创建备份、查询备份列表与下载备份文件。"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import get_admin_user
from app.models import User
from app.schemas.backup_out import BackupOut
from app.services.backup_service import BackupService

# 备份路由
router = APIRouter(prefix="/api/backups", tags=["数据备份"])


@router.get("", response_model=list[BackupOut])
def list_backups(_user: User = Depends(get_admin_user)):
    """列出全部备份文件（按时间倒序）。"""
    return BackupService.list_backups()


@router.post("", response_model=BackupOut, status_code=201)
def create_backup(_user: User = Depends(get_admin_user)):
    """立即创建一份数据库备份。"""
    try:
        return BackupService.create_backup()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{name}/download")
def download_backup(name: str, _user: User = Depends(get_admin_user)):
    """下载指定备份文件（恢复时由管理员手动替换数据库）。"""
    try:
        path = BackupService.get_file(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="备份文件不存在") from exc
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")
