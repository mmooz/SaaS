"""分类毛利行模型。"""

from pydantic import BaseModel


class ReportProfitRow(BaseModel):
    """分类毛利行：销售额、成本、毛利与毛利率。"""

    # 分类名称
    category: str
    # 销售额（元）
    sales: float = 0
    # 成本（元）
    cost: float = 0
    # 毛利（元）
    profit: float = 0
    # 毛利率（百分比 0-100）
    rate: float = 0
