"""超级管理员创建租户的请求模型。"""

from pydantic import BaseModel, Field, model_validator


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
    # 初始管理员密码（不再提供默认弱口令；填写管理员账号时必填且至少 8 位）
    admin_password: str | None = Field(None, min_length=8, max_length=100)
    # 初始管理员姓名
    admin_name: str | None = Field(None, max_length=50)

    @model_validator(mode="after")
    def _require_strong_admin_password(self) -> "TenantAdminCreate":
        """校验初始管理员密码强度，禁止回退到固定弱口令 123456。

        :return: 校验通过的请求模型本身
        :raises ValueError: 填写了管理员账号但密码缺失、过短或为常见弱口令
        """
        if self.admin_username and self.admin_username.strip():
            password = self.admin_password or ""
            if len(password.strip()) < 8:
                raise ValueError("创建初始管理员必须设置至少 8 位的密码")
            if password.strip().lower() in ("123456", "12345678", "123456789", "password", "admin123"):
                raise ValueError("初始管理员密码过于简单，请更换")
        return self
