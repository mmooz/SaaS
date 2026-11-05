"""促销规则输出模型。"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.snowflake_id import SnowflakeId


class PromotionOut(BaseModel):
    """促销规则响应体：JSON 字符串已解析为数组/对象。"""

    # 促销 ID
    id: SnowflakeId
    # 类型
    type: str
    # 名称
    name: str
    # 适用商品 ID 列表
    product_ids: list[SnowflakeId] | None
    # 适用分类 ID 列表
    category_ids: list[SnowflakeId] | None
    # 优惠参数
    params: dict
    # 生效开始时间
    start_at: datetime | None
    # 生效结束时间
    end_at: datetime | None
    # 是否启用
    enabled: bool
    # 预留门店 ID
    store_id: int
    # 创建时间
    created_at: datetime
