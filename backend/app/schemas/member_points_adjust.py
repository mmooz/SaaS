"""会员积分调整请求模型。"""

from pydantic import BaseModel, Field


class MemberPointsAdjust(BaseModel):
    """会员积分手工调整请求体：正数为增加，负数为扣减。"""

    # 积分变动值（正增负减，且不能为 0）
    points: int = Field(..., ne=0)
    # 调整原因（用于流水备注展示）
    operator_id: int | None = None
