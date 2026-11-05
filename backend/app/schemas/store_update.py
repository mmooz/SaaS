"""门店更新请求模型。"""

from pydantic import BaseModel, Field


class StoreUpdate(BaseModel):
    """更新门店请求体（仅修改传入字段）。"""

    # 门店名称
    name: str | None = Field(None, min_length=1, max_length=100)
    # 门店地址
    address: str | None = Field(None, max_length=255)
    # 联系电话
    phone: str | None = Field(None, max_length=30)
    # 是否启用
    enabled: bool | None = None
