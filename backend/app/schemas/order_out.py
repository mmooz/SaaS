"""订单输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.order_item_create import OrderItemCreate


class OrderOut(BaseModel):
    """订单响应体：含订单明细。"""

    model_config = ConfigDict(from_attributes=True)

    # 订单 ID
    id: int
    # 订单号
    order_no: str
    # 预留门店 ID
    store_id: int
    # 收银员用户 ID
    cashier_id: int | None
    # 交接班会话 ID
    shift_id: int | None
    # 订单状态
    status: str
    # 应收总额
    total_amount: float
    # 优惠金额
    discount_amount: float
    # 支付方式明细
    pay_details: str | None
    # 关联会员 ID
    member_id: int | None
    # 备注
    remark: str | None
    # 是否已同步
    synced: bool
    # 下单时间
    created_at: datetime
    # 订单明细
    items: list[OrderItemCreate] = []
