"""毛利分析响应模型。"""

from pydantic import BaseModel

from app.schemas.report_profit_row import ReportProfitRow


class ReportProfitOut(BaseModel):
    """毛利分析：整体毛利与分类明细。"""

    # 销售额（元）
    sales: float = 0
    # 成本（元）
    cost: float = 0
    # 毛利（元）
    profit: float = 0
    # 毛利率（百分比 0-100）
    rate: float = 0
    # 分类明细
    categories: list[ReportProfitRow]
