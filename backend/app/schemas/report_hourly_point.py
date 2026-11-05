"""时段分析点模型。"""

from pydantic import BaseModel


class ReportHourlyPoint(BaseModel):
    """时段点：某个小时的销售额与订单数。"""

    # 小时（0-23）
    hour: int
    # 展示标签（如 18:00）
    label: str
    # 销售额（元）
    sales: float = 0
    # 订单数
    orders: int = 0
