"""登录响应模型。"""

from pydantic import BaseModel

from app.schemas.user_out import UserOut


class LoginResponse(BaseModel):
    """登录成功响应：访问令牌与登录用户信息。"""

    # 访问令牌（后续请求放在 Authorization: Bearer 中）
    access_token: str
    # 令牌类型
    token_type: str = "bearer"
    # 令牌有效期（秒）
    expires_in: int
    # 登录用户信息
    user: UserOut
