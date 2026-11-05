"""时段分析响应模型。"""

from pydantic import BaseModel

from app.schemas.report_hourly_point import ReportHourlyPoint


class ReportHourlyOut(BaseModel):
    """时段分析：全天曲线与早晚高峰汇总。"""

    # 全天销售额（元）
    total_sales: float = 0
    # 高峰小时标签（如 18:00）
    peak_label: str = ""
    # 高峰小时销售额（元）
    peak_sales: float = 0
    # 早高峰销售额（8:00-11:00）
    morning_sales: float = 0
    # 午间销售额（11:00-15:00）
    noon_sales: float = 0
    # 晚高峰销售额（15:00-21:00）
    evening_sales: float = 0
    # 逐小时序列
    points: list[ReportHourlyPoint]
