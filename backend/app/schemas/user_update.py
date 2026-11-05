"""用户更新请求模型。"""

from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    """更新后台用户请求体：全部字段可选，仅更新传入字段。"""

    # 姓名
    name: str | None = Field(None, min_length=1, max_length=50)
    # 角色：admin=管理员，manager=店长，cashier=收银员
    role: str | None = Field(None, pattern="^(admin|manager|cashier)$")
    # 是否启用
    enabled: bool | None = None
    # 新密码（传入则重置密码）
    password: str | None = Field(None, min_length=6, max_length=64)
