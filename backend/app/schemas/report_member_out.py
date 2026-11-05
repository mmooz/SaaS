"""会员分析响应模型。"""

from pydantic import BaseModel

from app.schemas.report_member_row import ReportMemberRow


class ReportMemberOut(BaseModel):
    """会员分析：会员规模、消费贡献与复购率。"""

    # 会员总数
    member_total: int = 0
    # 区间新增会员数
    new_in_range: int = 0
    # 区间会员消费额（元）
    member_sales: float = 0
    # 区间会员消费笔数
    member_orders: int = 0
    # 会员消费占全部销售比例（百分比 0-100）
    member_ratio: float = 0
    # 会员复购率（百分比 0-100）
    repurchase_rate: float = 0
    # 会员消费排行
    items: list[ReportMemberRow]
