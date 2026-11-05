"""促销规则更新请求模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class PromotionUpdate(BaseModel):
    """更新促销规则请求体：仅修改传入字段。"""

    # 促销名称
    name: str | None = Field(None, min_length=1, max_length=80)
    # 适用商品 ID 列表
    product_ids: list[int] | None = None
    # 适用分类 ID 列表
    category_ids: list[int] | None = None
    # 优惠参数
    params: dict | None = None
    # 生效开始时间
    start_at: datetime | None = None
    # 生效结束时间
    end_at: datetime | None = None
    # 是否启用
    enabled: bool | None = None
