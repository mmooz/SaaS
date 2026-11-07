"""租户管理 API：超级管理员可管理全部租户，租户管理员仅可查看/修改本租户。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_admin_user, get_current_user, get_super_admin
from app.models import Tenant, User
from app.schemas.tenant_admin_create import TenantAdminCreate
from app.schemas.tenant_out import TenantOut
from app.schemas.tenant_stats_out import TenantStatsOut
from app.schemas.tenant_update import TenantUpdate
# 平台租户编码（超级管理员所在租户，不参与业务租户管理）
from app.services.tenant_service import PLATFORM_TENANT_CODE, TenantService

# 租户路由
router = APIRouter(prefix="/api/tenants", tags=["租户管理"])


def _to_error(exc: ValueError) -> HTTPException:
    """把服务层 ValueError 转换为 409 业务错误。

    :param exc: 服务层抛出的 ValueError
    :return: HTTPException 实例
    """
    return HTTPException(status_code=409, detail=str(exc))


@router.get("", response_model=list[TenantStatsOut])
def list_tenants(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询租户列表：超级管理员见全部业务租户，租户管理员仅见本租户。"""
    if user.role == "super":
        return TenantService.list_with_stats(db)

    tenant = db.get(Tenant, user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    return [TenantService.get_stats(db, tenant)]


@router.get("/{tenant_id}", response_model=TenantStatsOut)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询租户详情（超级管理员可查任意租户，租户管理员仅可查本租户）。"""
    if user.role != "super" and user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权查看该租户")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    return TenantService.get_stats(db, tenant)


@router.post("", response_model=TenantOut, status_code=201)
def create_tenant(
    data: TenantAdminCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_super_admin),
):
    """新增租户（仅平台超级管理员），可同时开通初始管理员账号。"""
    try:
        return TenantService.create(
            db,
            name=data.name,
            code=data.code,
            enabled=data.enabled,
            admin_username=data.admin_username,
            admin_password=data.admin_password,
            admin_name=data.admin_name,
        )
    except ValueError as exc:
        raise _to_error(exc) from exc


@router.patch("/{tenant_id}", response_model=TenantOut)
def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    """更新租户信息：超级管理员可改任意租户，租户管理员仅可改本租户名称。

    Q31：原实现只校验 user.tenant_id == tenant_id，无角色校验，收银员也能改
    租户名称/编码甚至 enabled=False。现要求 admin 及以上，且编码与启用状态
    仅平台超级管理员可变更。
    """
    if user.role != "super" and user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="只能修改所属租户")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    if tenant.code == PLATFORM_TENANT_CODE and user.role != "super":
        raise HTTPException(status_code=403, detail="平台租户不允许修改")
    if user.role != "super":
        # 前端编辑表单会原样回传 code / enabled，仅当值发生变化时才拒绝，
        # 避免「只改名称」被误伤
        payload = data.model_dump(exclude_unset=True)
        new_code = payload.get("code")
        if new_code and new_code.strip() != tenant.code:
            raise HTTPException(status_code=403, detail="仅平台超级管理员可修改租户编码")
        new_enabled = payload.get("enabled")
        if new_enabled is not None and new_enabled != tenant.enabled:
            raise HTTPException(status_code=403, detail="仅平台超级管理员可启用或停用租户")
    try:
        return TenantService.update(
            db, tenant, data, allow_sensitive=(user.role == "super")
        )
    except ValueError as exc:
        raise _to_error(exc) from exc


@router.get("/check-code/{code}", response_model=dict)
def check_code(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_super_admin),
):
    """校验租户编码是否可用（供新建表单实时提示）。"""
    exists = db.scalar(select(Tenant.id).where(Tenant.code == code.strip()))
    return {"code": code.strip(), "available": exists is None}
