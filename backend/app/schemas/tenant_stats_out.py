"""租户输出模型（含统计信息）。"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.snowflake_id import SnowflakeId


class TenantStatsOut(BaseModel):
    """租户列表/详情响应模型：附带门店数与用户数统计。"""

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
    # 门店数量
    store_count: int = 0
    # 用户数量
    user_count: int = 0
