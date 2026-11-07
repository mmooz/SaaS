"""离线班次补传单项模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ShiftSyncItem(BaseModel):
    """离线收银端上传的班次快照。"""

    # 班次主键（收银端离线生成的雪花 ID）
    id: int
    # 收银员用户 ID
    cashier_id: int
    # 班次发生门店（离线补传时可能取不到，留空则由服务端用当前上下文填充；
    # Q04：不再提供默认值 1，避免把班次静默归到错误门店）
    store_id: int | None = None
    # 接班时间
    start_at: datetime
    # 交班时间（空表示仍在进行）
    end_at: datetime | None = None
    # 现金底金
    base_cash: float = Field(0, ge=0)
    # 本班销售额
    total_sales: float = Field(0, ge=0)
    # 本班订单数
    order_count: int = Field(0, ge=0)
    # 状态：open=进行中，closed=已交班
    status: str = Field("open", pattern="^(open|closed)$")
