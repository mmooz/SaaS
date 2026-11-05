"""库存入库请求模型。"""

from pydantic import BaseModel, Field


class InventoryInbound(BaseModel):
    """采购入库请求体：商品、数量与进价。"""

    # 商品 ID
    product_id: int
    # 入库数量（称重商品的重量按 kg 计）
    qty: float = Field(..., gt=0)
    # 进价（可选，用于毛利统计与均价更新）
    cost_price: float | None = Field(None, ge=0)
    # 操作人用户 ID
    operator_id: int | None = None
