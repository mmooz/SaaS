"""用户创建请求模型。"""

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """新增后台用户请求体。"""

    # 登录用户名（全平台唯一，跨租户不可重名；登录按用户名全局查找）
    username: str = Field(..., min_length=2, max_length=50)
    # 姓名
    name: str = Field(..., min_length=1, max_length=50)
    # 角色：admin=管理员，manager=店长，cashier=收银员
    role: str = Field("cashier", pattern="^(admin|manager|cashier)$")
    # 初始密码（不传时使用默认密码 123456）
    password: str | None = Field(None, min_length=6, max_length=64)
