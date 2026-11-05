"""超级管理员创建租户的请求模型。"""

from pydantic import BaseModel, Field


class TenantAdminCreate(BaseModel):
    """超级管理员新增租户请求体（可同时开通初始管理员账号）。"""

    # 租户名称
    name: str = Field(..., min_length=1, max_length=100)
    # 租户编码（唯一标识）
    code: str = Field(..., min_length=2, max_length=50)
    # 是否启用
    enabled: bool = True
    # 初始管理员登录账号（为空则不创建管理员）
    admin_username: str | None = Field(None, max_length=50)
    # 初始管理员密码（为空时使用默认密码 123456）
    admin_password: str | None = Field(None, max_length=100)
    # 初始管理员姓名
    admin_name: str | None = Field(None, max_length=50)
