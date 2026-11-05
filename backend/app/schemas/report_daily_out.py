"""销售日报月报响应模型。"""

from pydantic import BaseModel

from app.schemas.report_sales_summary import ReportSalesSummary
from app.schemas.report_trend_point import ReportTrendPoint


class ReportDailyOut(BaseModel):
    """销售日报月报：区间汇总 + 趋势序列。"""

    # 区间汇总指标
    summary: ReportSalesSummary
    # 趋势序列（按日或按周）
    trend: list[ReportTrendPoint]
