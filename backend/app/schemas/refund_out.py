"""退款单输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.refund_item_out import RefundItemOut


class RefundOut(BaseModel):
    """退款单响应体：含退款明细。"""

    model_config = ConfigDict(from_attributes=True)

    # 退款单主键
    id: int
    # 退款单号
    refund_no: str
    # 原订单号
    order_no: str
    # 退款类型：full/item
    refund_type: str
    # 退款金额
    amount: float
    # 退款原因
    reason: str | None
    # 操作收银员用户 ID
    cashier_id: int | None
    # 店长授权人用户 ID
    authorizer_id: int | None
    # 退款时间
    created_at: datetime
    # 退款明细
    items: list[RefundItemOut] = []
