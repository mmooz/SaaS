"""会员充值请求模型。"""

from pydantic import BaseModel, Field


class MemberRecharge(BaseModel):
    """会员储值充值请求体：金额必须大于 0。

    Q02：赠送积分与操作人不再由客户端决定——bonus_points / operator_id 字段已移除，
    改由服务端 system_settings 配置与令牌上下文决定；客户端若仍传入这些字段，
    Pydantic 2 默认忽略额外字段，不会触发 422。

    R5 冻结登记（随 B4 / Q06 + Q20 收口，B3 **字段与逻辑一律不动**）：
    ``gift_amount`` 仍完全由客户端控制，仅受 ``MAX_RECHARGE_AMOUNT`` 单笔上限约束，
    缺服务端赠金梯度校验与频次 / 比例上限（后台梯度为前端硬编码）。拍板判定该项
    为资损必修但须与 Q06 结算接口、Q20 按比例退储值一并收口，B3 提前改动会返工；
    ``members.adjust_points`` 的 ``operator_id`` 取自请求体亦随 R5 在 B4 一并修。
    """

    # 充值金额（元）
    amount: float = Field(..., gt=0)
    # 赠送金额（元，参与余额累加）
    gift_amount: float = Field(0, ge=0)
