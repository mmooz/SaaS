"""库存报损请求模型。"""

from pydantic import BaseModel, Field


class InventoryBreakage(BaseModel):
    """报损请求体：扣减库存并记录报损流水。"""

    # 商品 ID
    product_id: int
    # 报损数量（称重商品按 kg）
    qty: float = Field(..., gt=0)
    # 操作人用户 ID
    operator_id: int | None = None
