"""登录响应模型。"""

from pydantic import BaseModel

from app.schemas.store_out import StoreOut
from app.schemas.user_out import UserOut


class LoginResponse(BaseModel):
    """登录成功响应：访问令牌、登录用户信息与可访问门店列表。"""

    # 访问令牌（后续请求放在 Authorization: Bearer 中）
    access_token: str
    # 令牌类型
    token_type: str = "bearer"
    # 令牌有效期（秒）
    expires_in: int
    # 登录用户信息
    user: UserOut
    # 用户可访问的门店列表（前端用于门店切换）
    stores: list[StoreOut]
    # R19：账号使用临时口令，前端须先进入改密流程再放行主界面。
    # 可选带默认值，旧客户端忽略该字段不影响既有登录逻辑。
    must_change_password: bool = False
