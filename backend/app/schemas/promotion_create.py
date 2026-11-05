"""促销规则创建请求模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class PromotionCreate(BaseModel):
    """新增促销规则请求体：类型 + 参数 JSON。"""

    # 类型：special=限时特价，discount=折扣，full_reduce=满减
    type: str = Field(..., pattern="^(special|discount|full_reduce)$")
    # 促销名称
    name: str = Field(..., min_length=1, max_length=80)
    # 适用商品 ID 列表（空表示不按商品限定）
    product_ids: list[int] | None = None
    # 适用分类 ID 列表（空表示不按分类限定）
    category_ids: list[int] | None = None
    # 优惠参数：特价 {price}、折扣 {rate}、满减 {threshold, reduce}
    params: dict = Field(default_factory=dict)
    # 生效开始时间
    start_at: datetime | None = None
    # 生效结束时间
    end_at: datetime | None = None
    # 是否启用
    enabled: bool = True
    # 预留门店 ID（多店扩展）
    store_id: int = 1
