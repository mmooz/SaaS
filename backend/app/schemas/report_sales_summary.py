"""销售汇总模型：报表区间的核心指标。"""

from pydantic import BaseModel


class ReportSalesSummary(BaseModel):
    """销售汇总：销售额、订单数、客单价、称重重量与称重订单数。"""

    # 销售额（元）
    sales: float = 0
    # 订单数
    orders: int = 0
    # 客单价（元）
    avg_price: float = 0
    # 称重重量合计（kg）
    weight_kg: float = 0
    # 含称重商品的订单数
    weighted_orders: int = 0
