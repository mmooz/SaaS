"""租户更新请求模型。"""

from pydantic import BaseModel, Field


class TenantUpdate(BaseModel):
    """更新租户请求体（仅修改传入字段）。"""

    # 租户名称
    name: str | None = Field(None, min_length=1, max_length=100)
    # 租户编码（唯一标识）
    code: str | None = Field(None, min_length=2, max_length=50)
    # 是否启用
    enabled: bool | None = None
