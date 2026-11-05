"""用户输出模型。"""

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class UserOut(BaseModel):
    """用户响应体：登录后可展示的身份信息（不含密码）。"""

    model_config = ConfigDict(from_attributes=True)

    # 用户 ID
    id: SnowflakeId
    # 登录账号（工号）
    username: str
    # 姓名
    name: str
    # 角色：admin=管理员，manager=店长，cashier=收银员
    role: str
