"""库存盘点请求模型。"""

from pydantic import BaseModel, Field


class InventoryStocktake(BaseModel):
    """盘点请求体：以实盘数覆盖当前库存并记录差异。"""

    # 商品 ID
    product_id: int
    # 实盘数量（称重商品按 kg）
    actual: float = Field(..., ge=0)
    # 操作人用户 ID
    operator_id: int | None = None
