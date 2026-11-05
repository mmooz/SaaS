"""批量改价请求模型。"""

from pydantic import BaseModel, Field


class BatchPriceRequest(BaseModel):
    """批量改价请求体：按分类或按商品选择范围，按比例或固定值调整。"""

    # 调整范围：category=按分类，product=按商品
    mode: str = Field(..., pattern="^(category|product)$")
    # 分类 ID（mode=category 时必填）
    category_id: int | None = None
    # 商品 ID 列表（mode=product 时必填）
    product_ids: list[int] = []
    # 调整方式：percent=按比例（如 10 表示 +10%），fixed=固定值（如 0.5 表示 +0.5 元）
    adjust_type: str = Field(..., pattern="^(percent|fixed)$")
    # 调整幅度：比例为正数表示百分比，固定值可为正负
    value: float = Field(..., ge=0)
