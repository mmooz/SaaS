"""退款请求模型：整单退款或按明细退货。"""

from pydantic import BaseModel, Field


class RefundCreate(BaseModel):
    """收银端退款请求体。"""

    # 退款类型：full=整单退款，item=单项退货
    refund_type: str = Field("full", pattern="^(full|item)$")
    # 退货明细主键列表（refund_type=item 时必填）
    item_ids: list[int] = []
    # 退款原因
    reason: str | None = Field(None, max_length=200)
    # 操作收银员用户 ID
    cashier_id: int | None = None
    # 店长授权人用户 ID（非本人当班订单退款时填写）
    authorizer_id: int | None = None
