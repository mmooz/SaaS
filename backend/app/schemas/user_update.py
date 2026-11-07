"""用户更新请求模型。"""

from pydantic import BaseModel, Field, field_validator

from app.services.password_policy import MIN_PASSWORD_LENGTH, ensure_strong_password


class UserUpdate(BaseModel):
    """更新后台用户请求体：全部字段可选，仅更新传入字段。"""

    # 姓名
    name: str | None = Field(None, min_length=1, max_length=50)
    # 角色：admin=管理员，manager=店长，cashier=收银员
    role: str | None = Field(None, pattern="^(admin|manager|cashier)$")
    # 是否启用
    enabled: bool | None = None
    # R8：新密码（传入则重置密码），同样不得回退到弱口令
    password: str | None = Field(None, min_length=MIN_PASSWORD_LENGTH, max_length=64)

    @field_validator("password")
    @classmethod
    def _check_password_strength(cls, value: str | None) -> str | None:
        """传入新密码时校验强度，未传（None）则不做校验。

        :param value: 新密码明文或 None
        :return: 校验通过的原文或 None
        :raises ValueError: 密码属于弱口令
        """
        if value is None:
            return None
        return ensure_strong_password(value, "新密码")
