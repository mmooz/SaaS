"""用户管理 API：账号列表、新增、更新与重置密码。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.user_admin_out import UserAdminOut
from app.schemas.user_create import UserCreate
from app.schemas.user_update import UserUpdate
from app.services.operation_log_service import OperationLogService
from app.services.password_hasher import PasswordHasher

# 用户路由
router = APIRouter(prefix="/api/users", tags=["用户管理"])

# 重置密码时使用的默认密码
DEFAULT_PASSWORD = "123456"


def _to_out(user: User) -> UserAdminOut:
    """把用户 ORM 对象转换为响应模型。

    :param user: 用户 ORM 对象
    :return: 用户管理响应体
    """
    return UserAdminOut.model_validate(user)


@router.get("", response_model=dict)
def list_users(
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """分页查询后台用户（支持用户名/姓名搜索）。"""
    stmt = select(User).order_by(User.id)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(or_(User.username.like(kw), User.name.like(kw)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    users = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_to_out(u) for u in users],
    }


@router.post("", response_model=UserAdminOut, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """新增后台用户（用户名唯一，密码默认 123456）。"""
    exists = db.scalar(select(User).where(User.username == data.username.strip()))
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(
        username=data.username.strip(),
        name=data.name.strip(),
        role=data.role,
        enabled=True,
        password_hash=PasswordHasher.hash(data.password or DEFAULT_PASSWORD),
    )
    db.add(user)
    db.flush()
    OperationLogService.record(db, "创建用户", f"新增用户 {user.username}（{user.role}）")
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db)):
    """更新用户姓名/角色/启用状态，可同时重置密码。"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    updates = data.model_dump(exclude_unset=True)
    # 密码单独处理，不直接写入字段
    password = updates.pop("password", None)
    for key, value in updates.items():
        setattr(user, key, value)
    if password:
        user.password_hash = PasswordHasher.hash(password)
    OperationLogService.record(db, "修改用户", f"更新用户 {user.username} 的资料")
    db.commit()
    db.refresh(user)
    return _to_out(user)


@router.post("/{user_id}/reset-password", response_model=UserAdminOut)
def reset_password(user_id: int, db: Session = Depends(get_db)):
    """把用户密码重置为默认密码 123456。"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = PasswordHasher.hash(DEFAULT_PASSWORD)
    OperationLogService.record(db, "重置密码", f"重置用户 {user.username} 的密码")
    db.commit()
    db.refresh(user)
    return _to_out(user)
