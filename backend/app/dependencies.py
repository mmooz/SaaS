"""全局依赖：从数据库解析当前用户、租户与门店上下文，供业务接口做数据隔离。

B1 / Q10：``tenant_id`` 不再取自令牌载荷 ``tid``（旧实现只验签不查库，掌握密钥者
可自签任意 tid 跨租户读数据），统一以数据库中的 ``user.tenant_id`` 为准并校验
``Tenant.enabled``；停用租户后已签发令牌立即失效。

B1 / Q30：平台超级管理员默认仍只属于平台租户，只有主动携带 ``X-Tenant-Id``
（目标业务租户，校验存在且启用）+ ``X-Store-Id`` 时才切换到该租户的门店上下文；
普通用户传入 ``X-Tenant-Id`` 一律忽略，避免成为新的越权入口。

B1 / Q33：角色层级统一为 super > admin > manager > cashier，要求 admin / manager
的接口显式放行 super；跨租户整库备份仍只归 super（见 api/backups.py）。
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import _current_user
from app.database import get_db
from app.models import Store, Tenant, User, UserStore


def get_authenticated_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(None),
) -> User:
    """仅解析登录态、不校验待改密标记的底层依赖。

    R19：待改密账号必须能凭借「临时口令登录换到的令牌」调用
    ``POST /api/auth/change-password``，因此该接口使用本依赖；
    其它任何业务接口都不应使用本依赖。

    :param db: 数据库会话
    :param authorization: Authorization 请求头
    :return: 登录用户 ORM 对象
    """
    return _current_user(db, authorization)


def get_current_user(user: User = Depends(get_authenticated_user)) -> User:
    """当前登录用户依赖：登录态校验 + R19 强制首次改密守卫。

    所有业务接口（角色层级、租户上下文、门店上下文）最终都经由本依赖，
    因此 ``must_change_password=True`` 的账号在本人改密前无法读写任何
    业务数据。守卫在服务端，不依赖前端是否配合跳转。

    :param user: 已解析的登录用户
    :return: 无需改密的登录用户 ORM 对象
    :raises HTTPException: 账号仍在使用临时口令（403）
    """
    if user.must_change_password:
        raise HTTPException(
            status_code=403,
            detail="账号当前使用临时口令，请先修改密码后再操作",
            headers={"X-Password-Change-Required": "1"},
        )
    return user


def get_tenant_id(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_tenant_id: int | None = Header(None, alias="X-Tenant-Id"),
) -> int:
    """解析当前请求所属租户：以数据库为准，令牌载荷中的 tid 不再参与。

    :param db: 数据库会话
    :param user: 当前登录用户（由令牌解析并查库得到）
    :param x_tenant_id: 仅平台超级管理员可用来显式切换目标业务租户
    :return: 租户 ID
    :raises HTTPException: 租户不存在或已停用
    """
    # 平台超级管理员的跨租户通道：必须显式指定目标租户，且目标租户须启用
    if user.role == "super" and x_tenant_id is not None:
        target = db.get(Tenant, x_tenant_id)
        if not target or not target.enabled:
            raise HTTPException(status_code=403, detail="目标租户不存在或已停用")
        return target.id

    tenant = db.get(Tenant, user.tenant_id)
    if not tenant or not tenant.enabled:
        raise HTTPException(status_code=403, detail="租户不存在或已停用")
    return tenant.id


def get_super_admin(user: User = Depends(get_current_user)) -> User:
    """要求当前登录用户为平台超级管理员。

    :param user: 当前登录用户
    :return: 超级管理员用户 ORM 对象
    """
    if user.role != "super":
        raise HTTPException(status_code=403, detail="仅平台超级管理员可执行该操作")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """要求当前登录用户为租户管理员及以上（admin / super）。

    :param user: 当前登录用户
    :return: 租户管理员及以上角色的用户 ORM 对象
    """
    if user.role not in ("admin", "super"):
        raise HTTPException(status_code=403, detail="仅租户管理员及以上角色可执行该操作")
    return user


def get_manager_user(user: User = Depends(get_current_user)) -> User:
    """要求当前登录用户为店长及以上（manager / admin / super）。

    :param user: 当前登录用户
    :return: 店长及以上角色的用户 ORM 对象
    """
    if user.role not in ("admin", "manager", "super"):
        raise HTTPException(status_code=403, detail="仅店长及以上角色可执行该操作")
    return user


def get_store_id(
    x_store_id: int | None = Header(None, alias="X-Store-Id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_id),
) -> int:
    """从请求头 X-Store-Id 获取门店 ID，并校验归属当前解析出的租户且用户可访问。

    :param x_store_id: 请求头传入的门店 ID
    :param db: 数据库会话
    :param user: 当前登录用户
    :param tenant_id: 由 get_tenant_id 解析出的租户 ID（不再用 user.tenant_id 直比，
        以兼容超级管理员通过 X-Tenant-Id 切换租户的场景）
    :return: 门店 ID
    """
    if x_store_id is None:
        raise HTTPException(status_code=400, detail="缺少 X-Store-Id 请求头")
    store = db.get(Store, x_store_id)
    if not store or store.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="无权访问该门店")
    # 校验用户是否被授权访问该门店（租户管理员与平台超级管理员放行）
    if user.role not in ("admin", "super"):
        allowed = db.scalar(
            select(UserStore.id).where(
                UserStore.user_id == user.id, UserStore.store_id == x_store_id
            )
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="无权访问该门店")
    return x_store_id
