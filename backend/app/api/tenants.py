"""租户管理 API：租户增删改查（管理员操作）。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_id
from app.models import Tenant, User
from app.schemas.tenant_create import TenantCreate
from app.schemas.tenant_out import TenantOut

# 租户路由
router = APIRouter(prefix="/api/tenants", tags=["租户管理"])


def _require_admin(user: User) -> None:
    """校验当前用户是否为管理员，否则抛 403。

    :param user: 当前登录用户
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作租户")


@router.get("", response_model=list[TenantOut])
def list_tenants(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询租户列表（管理员可见全部，普通用户仅见所属租户）。"""
    if user.role == "admin":
        rows = db.scalars(select(Tenant).order_by(Tenant.id.desc())).all()
    else:
        rows = db.scalars(select(Tenant).where(Tenant.id == user.tenant_id)).all()
    return [TenantOut.model_validate(t) for t in rows]


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询租户详情（仅可查看所属租户，管理员可查看任意）。"""
    if user.role != "admin" and user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权查看该租户")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    return tenant


@router.post("", response_model=TenantOut, status_code=201)
def create_tenant(
    data: TenantCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """新增租户（仅管理员）。"""
    _require_admin(user)
    # 编码唯一性校验
    existing = db.scalar(select(Tenant).where(Tenant.code == data.code.strip()))
    if existing:
        raise HTTPException(status_code=409, detail="租户编码已存在")
    tenant = Tenant(
        name=data.name.strip(),
        code=data.code.strip(),
        enabled=data.enabled,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}", response_model=TenantOut)
def update_tenant(
    tenant_id: int,
    data: TenantCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新租户信息（仅管理员，且只能修改所属租户）。"""
    _require_admin(user)
    if user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="只能修改所属租户")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    # 编码唯一性校验（排除自身）
    if data.code.strip() != tenant.code:
        dup = db.scalar(
            select(Tenant).where(Tenant.code == data.code.strip(), Tenant.id != tenant_id)
        )
        if dup:
            raise HTTPException(status_code=409, detail="租户编码已存在")
    tenant.name = data.name.strip()
    tenant.code = data.code.strip()
    tenant.enabled = data.enabled
    db.commit()
    db.refresh(tenant)
    return tenant
