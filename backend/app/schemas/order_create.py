"""订单创建请求模型。"""

from pydantic import BaseModel, Field

from app.schemas.order_item_create import OrderItemCreate


class OrderCreate(BaseModel):
    """收银端上传订单请求体。"""

    # 订单号（收银端生成，唯一，用于幂等去重）
    order_no: str = Field(..., min_length=1, max_length=32)
    # 预留门店 ID（多店扩展）
    store_id: int = 1
    # 收银员用户 ID
    cashier_id: int | None = None
    # 交接班会话 ID
    shift_id: int | None = None
    # 订单状态：pending/paid/refunded
    status: str = Field("paid", pattern="^(pending|paid|refunded)$")
    # 应收总额
    total_amount: float = Field(0, ge=0)
    # 优惠金额
    discount_amount: float = 0
    # 支付方式明细（JSON 字符串或原始字符串）
    pay_details: str | None = None
    # 关联会员 ID
    member_id: int | None = None
    # 备注
    remark: str | None = Field(None, max_length=200)
    # 订单明细
    items: list[OrderItemCreate] = []
