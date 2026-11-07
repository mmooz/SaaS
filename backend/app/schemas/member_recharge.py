"""会员充值请求模型。"""

from pydantic import BaseModel, Field


class MemberRecharge(BaseModel):
    """会员储值充值请求体：金额必须大于 0。

    Q02：赠送积分与操作人不再由客户端决定——bonus_points / operator_id 字段已移除，
    改由服务端 system_settings 配置与令牌上下文决定；客户端若仍传入这些字段，
    Pydantic 2 默认忽略额外字段，不会触发 422。
    """

    # 充值金额（元）
    amount: float = Field(..., gt=0)
    # 赠送金额（元，参与余额累加）
    gift_amount: float = Field(0, ge=0)
