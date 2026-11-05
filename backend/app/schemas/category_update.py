"""分类更新请求模型。"""

from pydantic import BaseModel, Field


class CategoryUpdate(BaseModel):
    """更新分类请求体：全部字段可选，仅更新传入的字段。"""

    # 分类名称
    name: str | None = Field(None, min_length=1, max_length=50)
    # 上级分类 ID（空表示一级分类）
    parent_id: int | None = None
    # 排序值
    sort: int | None = None
    # 是否启用
    enabled: bool | None = None
