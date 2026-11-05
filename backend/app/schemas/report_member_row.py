"""会员消费排行行模型。"""

from pydantic import BaseModel


class ReportMemberRow(BaseModel):
    """会员消费行：消费笔数、金额与占比。"""

    # 会员 ID
    member_id: int
    # 会员姓名
    name: str
    # 会员等级：normal/silver/gold
    level: str
    # 消费笔数
    orders: int = 0
    # 消费金额（元）
    amount: float = 0
    # 消费金额占比（百分比 0-100）
    ratio: float = 0
