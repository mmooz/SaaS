"""租户创建请求模型。"""

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    """新增租户请求体。"""

    # 租户名称
    name: str = Field(..., min_length=1, max_length=100)
    # 租户编码（唯一标识）
    code: str = Field(..., min_length=2, max_length=50)
    # 是否启用
    enabled: bool = True
