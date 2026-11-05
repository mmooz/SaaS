"""后台用户管理输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class UserAdminOut(BaseModel):
    """用户管理响应体：包含启用状态与创建时间（不含密码）。"""

    model_config = ConfigDict(from_attributes=True)

    # 用户 ID
    id: SnowflakeId
    # 登录用户名
    username: str
    # 姓名
    name: str
    # 角色：admin=管理员，manager=店长，cashier=收银员
    role: str
    # 是否启用
    enabled: bool
    # 创建时间
    created_at: datetime
