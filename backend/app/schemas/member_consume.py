"""会员消费请求模型。"""

from pydantic import BaseModel, Field


class MemberConsume(BaseModel):
    """会员消费请求体：扣储值余额并按金额累计积分。"""

    # 消费金额（元）
    amount: float = Field(..., gt=0)
    # 关联订单号（用于对账追溯）
    order_no: str | None = Field(None, max_length=32)
    # 每消费 1 元获得的积分（默认 1 分）
    points_per_yuan: float = Field(1, ge=0)
    # 操作人用户 ID
    operator_id: int | None = None
