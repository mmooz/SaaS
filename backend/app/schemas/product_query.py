"""商品列表查询参数模型。"""

from pydantic import BaseModel, Field


class ProductQuery(BaseModel):
    """商品列表筛选与分页参数（Query 参数）。"""

    # 关键字（匹配条码/名称/拼音码）
    keyword: str | None = None
    # 分类 ID 筛选
    category_id: int | None = None
    # 计价方式筛选
    pricing_mode: str | None = Field(None, pattern="^(weigh|count)$")
    # 是否仅启用
    enabled: bool | None = None
    # 页码（从 1 开始）
    page: int = Field(1, ge=1)
    # 每页数量
    page_size: int = Field(20, ge=1, le=200)
