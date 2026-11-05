"""退款明细输出模型。"""

from pydantic import BaseModel, ConfigDict


class RefundItemOut(BaseModel):
    """退款明细响应体：被退商品行快照。"""

    model_config = ConfigDict(from_attributes=True)

    # 退款明细主键
    id: int
    # 原订单明细主键
    order_item_id: int | None
    # 商品名称
    name: str
    # 退货数量（按件商品）
    qty: int
    # 退货重量 kg（称重商品）
    weight_kg: float | None
    # 退款金额
    amount: float
    # 是否称重商品
    is_weighted: bool
