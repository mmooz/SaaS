"""班次输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShiftOut(BaseModel):
    """班次响应体。"""

    model_config = ConfigDict(from_attributes=True)

    # 班次主键
    id: int
    # 收银员用户 ID
    cashier_id: int
    # 接班时间
    start_at: datetime
    # 交班时间（空表示进行中）
    end_at: datetime | None
    # 现金底金
    base_cash: float
    # 本班销售额
    total_sales: float
    # 本班订单数
    order_count: int
    # 状态：open/closed
    status: str
