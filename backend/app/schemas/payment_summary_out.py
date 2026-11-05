"""支付方式汇总输出模型。"""

from pydantic import BaseModel


class PaymentSummaryOut(BaseModel):
    """按支付方式汇总的金额与笔数。"""

    # 支付方式名称
    method: str
    # 金额
    amount: float
    # 笔数
    count: int
