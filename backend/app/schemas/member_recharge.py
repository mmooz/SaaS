"""会员充值请求模型。"""

from pydantic import BaseModel, Field


class MemberRecharge(BaseModel):
    """会员储值充值请求体：金额必须大于 0。"""

    # 充值金额（元）
    amount: float = Field(..., gt=0)
    # 赠送金额（元，参与余额累加）
    gift_amount: float = Field(0, ge=0)
    # 赠送积分（可选，按活动手工填写）
    bonus_points: int = Field(0, ge=0)
    # 操作人用户 ID
    operator_id: int | None = None
