"""分类输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class CategoryOut(BaseModel):
    """分类响应体：包含递归子分类结构。"""

    model_config = ConfigDict(from_attributes=True)

    # 分类 ID
    id: SnowflakeId
    # 分类名称
    name: str
    # 上级分类 ID
    parent_id: SnowflakeId | None
    # 排序值
    sort: int
    # 是否启用
    enabled: bool
    # 预留门店 ID
    store_id: int
    # 创建时间
    created_at: datetime
    # 子分类（递归）
    children: list["CategoryOut"] = []
