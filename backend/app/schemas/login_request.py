"""登录请求模型。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求体：登录账号与密码。"""

    # 登录账号（工号）
    username: str = Field(..., min_length=1, max_length=50)
    # 登录密码
    password: str = Field(..., min_length=1, max_length=100)
