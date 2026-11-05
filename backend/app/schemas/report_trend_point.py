"""销售趋势点模型：按日/按周的销售额与订单数。"""

from pydantic import BaseModel


class ReportTrendPoint(BaseModel):
    """销售趋势点：一个日期或一周的汇总。"""

    # 展示标签（日期 或 第N周）
    label: str
    # 销售额（元）
    sales: float = 0
    # 订单数
    orders: int = 0
