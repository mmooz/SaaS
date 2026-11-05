"""门店创建请求模型。"""

from pydantic import BaseModel, Field


class StoreCreate(BaseModel):
    """新增门店请求体（归属当前登录用户的租户）。"""

    # 门店名称
    name: str = Field(..., min_length=1, max_length=100)
    # 门店地址
    address: str | None = Field(None, max_length=255)
    # 联系电话
    phone: str | None = Field(None, max_length=30)
    # 是否启用
    enabled: bool = True
