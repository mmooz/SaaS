"""用户创建请求模型。"""

from pydantic import BaseModel, Field, field_validator

from app.services.password_policy import MIN_PASSWORD_LENGTH, ensure_strong_password


class UserCreate(BaseModel):
    """新增后台用户请求体。"""

    # 登录用户名（全平台唯一，跨租户不可重名；登录按用户名全局查找）
    username: str = Field(..., min_length=2, max_length=50)
    # 姓名
    name: str = Field(..., min_length=1, max_length=50)
    # 角色：admin=管理员，manager=店长，cashier=收银员
    role: str = Field("cashier", pattern="^(admin|manager|cashier)$")
    # R8：初始密码必填且至少 8 位，不再提供任何默认弱口令
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=64)

    @field_validator("password")
    @classmethod
    def _check_password_strength(cls, value: str) -> str:
        """拒绝常见弱口令（与租户初始管理员、口令轮换脚本共用规则）。

        :param value: 初始密码明文
        :return: 校验通过的原文
        :raises ValueError: 密码属于弱口令
        """
        return ensure_strong_password(value, "初始密码")
