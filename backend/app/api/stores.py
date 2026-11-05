"""门店管理 API：门店增删改查与用户门店授权（管理员操作）。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_id
from app.models import Store, User, UserStore
from app.schemas.store_create import StoreCreate
from app.schemas.store_out import StoreOut
from app.schemas.store_update import StoreUpdate

# 门店路由
router = APIRouter(prefix="/api/stores", tags=["门店管理"])


def _require_admin(user: User) -> None:
    """校验当前用户是否为管理员，否则抛 403。

    :param user: 当前登录用户
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作门店")


@router.get("", response_model=list[StoreOut])
def list_stores(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """查询当前租户下的全部门店。"""
    rows = db.scalars(
        select(Store).where(Store.tenant_id == tenant_id).order_by(Store.id.desc())
    ).all()
    return [StoreOut.model_validate(s) for s in rows]


@router.post("", response_model=StoreOut, status_code=201)
def create_store(
    data: StoreCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user: User = Depends(get_current_user),
):
    """新增门店（仅管理员，归属当前租户）。"""
    _require_admin(user)
    store = Store(
        tenant_id=tenant_id,
        name=data.name.strip(),
        address=data.address,
        phone=data.phone,
        enabled=data.enabled,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.patch("/{store_id}", response_model=StoreOut)
def update_store(
    store_id: int,
    data: StoreUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user: User = Depends(get_current_user),
):
    """更新门店信息（仅管理员，限定当前租户）。"""
    _require_admin(user)
    store = db.scalar(
        select(Store).where(Store.id == store_id, Store.tenant_id == tenant_id)
    )
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(store, key, value)
    db.commit()
    db.refresh(store)
    return store


@router.delete("/{store_id}", status_code=204)
def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user: User = Depends(get_current_user),
):
    """删除门店（仅管理员，限定当前租户，删除前清除用户授权）。"""
    _require_admin(user)
    store = db.scalar(
        select(Store).where(Store.id == store_id, Store.tenant_id == tenant_id)
    )
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    # 清除该门店的所有用户授权
    db.execute(delete(UserStore).where(UserStore.store_id == store_id))
    db.delete(store)
    db.commit()


@router.get("/{store_id}/users", response_model=list)
def list_store_users(
    store_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    """查询被授权访问该门店的用户列表。"""
    store = db.scalar(
        select(Store).where(Store.id == store_id, Store.tenant_id == tenant_id)
    )
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    user_ids = db.scalars(
        select(UserStore.user_id).where(UserStore.store_id == store_id)
    ).all()
    if not user_ids:
        return []
    users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
    return [
        {"id": str(u.id), "username": u.username, "name": u.name, "role": u.role}
        for u in users
    ]


@router.post("/{store_id}/users/{user_id}", status_code=201)
def grant_store_access(
    store_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user: User = Depends(get_current_user),
):
    """授权用户访问指定门店（仅管理员，用户须属同一租户）。"""
    _require_admin(user)
    store = db.scalar(
        select(Store).where(Store.id == store_id, Store.tenant_id == tenant_id)
    )
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    target = db.scalar(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 已授权则跳过
    existing = db.scalar(
        select(UserStore).where(
            UserStore.user_id == user_id, UserStore.store_id == store_id
        )
    )
    if not existing:
        db.add(UserStore(user_id=user_id, store_id=store_id))
        db.commit()
    return {"message": "授权成功"}


@router.delete("/{store_id}/users/{user_id}", status_code=204)
def revoke_store_access(
    store_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    user: User = Depends(get_current_user),
):
    """撤销用户对指定门店的访问权限（仅管理员）。"""
    _require_admin(user)
    db.execute(
        delete(UserStore).where(
            UserStore.user_id == user_id, UserStore.store_id == store_id
        )
    )
    db.commit()
