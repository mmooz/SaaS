"""会员流水输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MemberTransactionOut(BaseModel):
    """会员流水响应体：展示充值/消费/积分变动明细。"""

    model_config = ConfigDict(from_attributes=True)

    # 流水 ID
    id: int
    # 关联会员 ID
    member_id: int
    # 类型：recharge/consume/refund/points
    type: str
    # 金额变动
    amount: float
    # 积分变动
    points: int
    # 操作人用户 ID
    operator_id: int | None
    # 流水时间
    created_at: datetime
