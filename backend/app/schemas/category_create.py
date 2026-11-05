"""分类创建请求模型。"""

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """新增分类请求体。"""

    # 分类名称
    name: str = Field(..., min_length=1, max_length=50)
    # 上级分类 ID（空表示一级分类）
    parent_id: int | None = None
    # 排序值（越小越靠前）
    sort: int = 0
    # 是否启用
    enabled: bool = True
    # 预留门店 ID（多店扩展）
    store_id: int = 1
