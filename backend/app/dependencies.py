"""全局依赖：从令牌解析当前用户、租户与门店，供业务接口做数据隔离。"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import token_service, _current_user
from app.database import get_db
from app.models import Store, User, UserStore


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> User:
    """当前登录用户依赖。

    :param db: 数据库会话
    :param authorization: Authorization 请求头
    :return: 登录用户 ORM 对象
    """
    return _current_user(db, authorization)


def get_tenant_id(
    authorization: str | None = Header(None),
) -> int:
    """从令牌解析所属租户 ID。

    :param authorization: Authorization 请求头
    :return: 租户 ID
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    payload = token_service.verify(authorization[7:].strip())
    if payload is None:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return payload["tenant_id"]


def get_store_id(
    x_store_id: int | None = Header(None, alias="X-Store-Id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> int:
    """从请求头 X-Store-Id 获取当前门店 ID，并校验该门店属于当前租户且用户可访问。

    :param x_store_id: 请求头传入的门店 ID
    :param db: 数据库会话
    :param user: 当前登录用户
    :return: 门店 ID
    """
    if x_store_id is None:
        raise HTTPException(status_code=400, detail="缺少 X-Store-Id 请求头")
    # 校验门店归属租户
    store = db.get(Store, x_store_id)
    if not store or store.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该门店")
    # 校验用户是否被授权访问该门店（管理员放行）
    if user.role != "admin":
        allowed = db.scalar(
            select(UserStore.id).where(
                UserStore.user_id == user.id, UserStore.store_id == x_store_id
            )
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="无权访问该门店")
    return x_store_id
