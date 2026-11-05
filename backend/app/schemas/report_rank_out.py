"""商品销售排行响应模型。"""

from pydantic import BaseModel

from app.schemas.report_rank_row import ReportRankRow


class ReportRankOut(BaseModel):
    """商品销售排行：总销售额与排行列表。"""

    # 区间总销售额（元）
    total_amount: float = 0
    # 排行明细
    items: list[ReportRankRow]
