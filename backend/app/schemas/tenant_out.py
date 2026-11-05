"""租户输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class TenantOut(BaseModel):
    """租户信息响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    # 租户 ID
    id: SnowflakeId
    # 租户名称
    name: str
    # 租户编码
    code: str
    # 是否启用
    enabled: bool
    # 创建时间
    created_at: datetime
