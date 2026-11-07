"""会员消费请求模型。"""

from pydantic import BaseModel, Field


class MemberConsume(BaseModel):
    """会员消费请求体：扣储值余额并按金额累计积分。

    Q02：积分换算比例与操作人不再由客户端决定——points_per_yuan / operator_id
    字段已移除，改由服务端 system_settings 配置与令牌上下文决定；客户端若仍传入
    这些字段，Pydantic 2 默认忽略额外字段，不会触发 422。
    """

    # 消费金额（元）
    amount: float = Field(..., gt=0)
    # 关联订单号（用于对账追溯）
    order_no: str | None = Field(None, max_length=32)
