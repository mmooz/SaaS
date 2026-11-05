"""班次汇总输出模型：交班小票所需数据。"""

from pydantic import BaseModel, ConfigDict

from app.schemas.payment_summary_out import PaymentSummaryOut
from app.schemas.shift_out import ShiftOut


class ShiftSummaryOut(BaseModel):
    """班次汇总响应体。"""

    model_config = ConfigDict(from_attributes=True)

    # 班次信息
    shift: ShiftOut
    # 订单总数
    order_count: int
    # 本班销售额（扣除退款）
    total_sales: float
    # 退款金额
    refund_amount: float
    # 各支付方式汇总
    payments: list[PaymentSummaryOut]
    # 现金应交（底金 + 现金收入）
    cash_should: float
    # 实际点钞现金（未填为 null）
    actual_cash: float | None = None
