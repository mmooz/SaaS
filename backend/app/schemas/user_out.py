"""用户输出模型。"""

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class UserOut(BaseModel):
    """用户响应体：登录后可展示的身份信息（不含密码）。"""

    model_config = ConfigDict(from_attributes=True)

    # 用户 ID
    id: SnowflakeId
    # 所属租户 ID
    tenant_id: SnowflakeId
    # 登录账号（工号）
    username: str
    # 姓名
    name: str
    # 角色：super=平台超级管理员，admin=租户管理员，manager=店长，cashier=收银员
    role: str
    # R19：是否仍需先修改密码（供 /api/auth/me 恢复登录态时判断）
    must_change_password: bool = False
