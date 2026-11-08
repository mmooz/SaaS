"""登录认证 API：账号密码登录、令牌换取当前用户信息、强制首次改密（R19）。"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Store, User, UserStore
from app.schemas.change_password import ChangePasswordOut, ChangePasswordRequest
from app.schemas.login_request import LoginRequest
from app.schemas.login_response import LoginResponse
from app.schemas.store_out import StoreOut
from app.schemas.user_out import UserOut
from app.services.password_hasher import PasswordHasher
from app.services.operation_log_service import OperationLogService
from app.services.token_service import TokenService

# 登录路由
router = APIRouter(prefix="/api/auth", tags=["登录认证"])

# 令牌服务实例（密钥与有效期来自配置）
token_service = TokenService(settings.auth_secret, settings.auth_expire_hours)


def _current_user(db: Session, authorization: str | None) -> User:
    """按请求头中的 Bearer 令牌解析当前登录用户。

    :param db: 数据库会话
    :param authorization: Authorization 请求头
    :return: 登录用户 ORM 对象
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    payload = token_service.verify(authorization[7:].strip())
    if payload is None:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    user = db.get(User, payload["user_id"])
    if not user or not user.enabled:
        raise HTTPException(status_code=401, detail="账号不存在或已停用")
    # R19：令牌与其签发时的密码版本绑定。轮换弱口令 / 管理员重置 / 本人改密后，
    # 库中哈希变化会使所有此前签发的令牌立即失效（含用旧临时口令换到的令牌）。
    if token_service.password_version(user.password_hash) != payload.get(
        "password_version", ""
    ):
        raise HTTPException(status_code=401, detail="密码已变更，请重新登录")
    return user


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """账号密码登录：校验通过后签发令牌并返回用户信息与可访问门店。"""
    user = db.scalar(select(User).where(User.username == data.username.strip()))
    # 账号不存在与密码错误统一提示，避免暴露账号是否存在
    if not user or not PasswordHasher.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    # 停用账号禁止登录
    if not user.enabled:
        raise HTTPException(status_code=403, detail="账号已停用，请联系管理员")
    # 查询用户可访问的门店列表
    store_ids = db.scalars(
        select(UserStore.store_id).where(UserStore.user_id == user.id)
    ).all()
    stores = (
        db.scalars(select(Store).where(Store.id.in_(store_ids))).all() if store_ids else []
    )
    # 记录登录日志
    OperationLogService.record(
        db, "登录", f"用户 {user.username} 登录成功", user.id, tenant_id=user.tenant_id
    )
    db.commit()
    return LoginResponse(
        access_token=token_service.issue(user.id, user.tenant_id, user.password_hash),
        expires_in=token_service.expire_seconds,
        user=UserOut.model_validate(user),
        stores=[StoreOut.model_validate(s) for s in stores],
        must_change_password=bool(user.must_change_password),
    )


@router.get("/me", response_model=UserOut)
def current_user(
    authorization: str | None = Header(None), db: Session = Depends(get_db)
):
    """按令牌查询当前登录用户（用于前端恢复登录状态时校验）。

    R19：本接口不经过业务守卫，待改密账号仍能读到 ``must_change_password``，
    前端据此在恢复登录态时也能正确跳回改密流程。
    """
    return UserOut.model_validate(_current_user(db, authorization))


def _authenticated_user_dep(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """改密接口专用依赖：只校验登录态，不触发 R19 业务守卫。

    不能直接复用 ``get_current_user``，否则待改密账号会被守卫 403 拒绝，
    永远无法完成改密；也不能从 ``app.dependencies`` 导入，因为那里反向
    依赖 ``app.api.auth._current_user``，会形成循环导入。

    :param authorization: Authorization 请求头
    :param db: 数据库会话
    :return: 登录用户 ORM 对象
    """
    return _current_user(db, authorization)


@router.post("/change-password", response_model=ChangePasswordOut)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_authenticated_user_dep),
):
    """R19：本人凭原密码设置新密码并清除强制改密标记。

    适用于「历史弱口令轮换 / 管理员重置出临时口令 / 新建账号」三类场景，
    也允许普通账号自助改密。新密码强度与「新旧不能相同」由
    ``ChangePasswordRequest`` 统一校验；成功后因令牌绑定密码版本，所有
    旧令牌立即失效，客户端须用新密码重新登录。

    :param data: 原密码与新密码
    :param db: 数据库会话
    :param user: 当前登录用户
    :return: 清除后的强制改密标记
    :raises HTTPException: 原密码不正确（400）
    """
    if not PasswordHasher.verify(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    user.password_hash = PasswordHasher.hash(data.new_password)
    user.must_change_password = False
    OperationLogService.record(
        db,
        "修改密码",
        f"用户 {user.username} 修改登录密码",
        user.id,
        tenant_id=user.tenant_id,
    )
    db.commit()
    return ChangePasswordOut(must_change_password=False)
